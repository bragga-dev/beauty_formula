"""
Testes de apps.payment.services.payment_service.

Cobre os caminhos que os 3 testes pré-existentes de
`test_asaas_integration_fixes.py` não tocam: o webhook da Asaas, o
estorno, a criação de cobrança (incluindo o rollback compensatório) e o
cancelamento de cobrança pendente. `AsaasClient` é sempre mockado — nada
aqui bate na API real da Asaas.
"""
from decimal import Decimal
from unittest.mock import patch

import pytest
from django.test import TestCase

from beauty_formula.apps.core.exceptions.payment_exception import (
    AsaasAPIError,
    CpfOrCnpjRequired,
    PaymentNotFound,
    PaymentNotRefundable,
    SchedulingAlreadyPaid,
)
from beauty_formula.apps.core.exceptions.service_exception import SchedulingConflict
from beauty_formula.apps.payment.models.payment_model import Payment
from beauty_formula.apps.payment.selectors.payment_selector import get_payment_by_id
from beauty_formula.apps.payment.services.payment_service import (
    cancel_payment_for_scheduling,
    create_charge_for_scheduling,
    process_asaas_webhook,
    refund_payment,
    sync_payment_with_asaas,
)
from beauty_formula.apps.services.models.scheduling import Scheduling


pytestmark = pytest.mark.django_db


# ═══════════════════════════════════════════════════════════════════════════════
# process_asaas_webhook
# ═══════════════════════════════════════════════════════════════════════════════

class ProcessAsaasWebhookTests(TestCase):
    def test_payload_missing_id_raises(self):
        with self.assertRaises(PaymentNotFound):
            process_asaas_webhook({"payment": {"status": "RECEIVED"}})

    def test_payload_missing_status_raises(self):
        with self.assertRaises(PaymentNotFound):
            process_asaas_webhook({"payment": {"id": "pay_123"}})

    def test_payload_without_payment_key_raises(self):
        with self.assertRaises(PaymentNotFound):
            process_asaas_webhook({})

    def test_unknown_asaas_payment_id_raises(self):
        with self.assertRaises(PaymentNotFound):
            process_asaas_webhook({"payment": {"id": "pay_desconhecido", "status": "RECEIVED"}})


@pytest.mark.django_db
class TestProcessAsaasWebhookConfirmsScheduling:
    """
    Casos que precisam de um Payment/Scheduling reais no banco — usando
    classe de teste em estilo pytest (fixtures via injeção de parâmetro)
    em vez de TestCase, que não aceita fixtures do conftest diretamente.
    """

    def test_received_status_confirms_scheduling(self, pending_payment):
        result = process_asaas_webhook({"payment": {"id": pending_payment.asaas_payment_id, "status": "RECEIVED"}})

        assert result.status == Payment.PaymentStatus.RECEIVED
        assert result.payment_date is not None

        scheduling = Scheduling.objects.get(pk=pending_payment.scheduling_id)
        assert scheduling.status == Scheduling.SchedulingStatus.CONFIRMED

    def test_overdue_status_does_not_confirm_scheduling(self, pending_payment):
        process_asaas_webhook({"payment": {"id": pending_payment.asaas_payment_id, "status": "OVERDUE"}})

        scheduling = Scheduling.objects.get(pk=pending_payment.scheduling_id)
        assert scheduling.status == Scheduling.SchedulingStatus.CREATED

    def test_scheduling_conflict_on_confirmation_does_not_raise(self, pending_payment):
        """
        Caso mais delicado do sistema: o pagamento chegou (dinheiro
        recebido de verdade), mas o agendamento não pode mais ser
        confirmado porque o horário foi ocupado por outro agendamento
        confirmado nesse meio-tempo. O webhook precisa devolver 200 pra
        Asaas de qualquer forma (senão ela fica reentregando o evento) —
        o Payment tem que ficar marcado como pago mesmo assim, e o erro
        só é logado, nunca propagado.
        """
        with patch(
            "beauty_formula.apps.services.services.scheduling_service.confirm_scheduling_after_payment",
            side_effect=SchedulingConflict("horário ocupado"),
        ):
            result = process_asaas_webhook({"payment": {"id": pending_payment.asaas_payment_id, "status": "CONFIRMED"}})

        assert result.status == Payment.PaymentStatus.CONFIRMED

    def test_webhook_is_idempotent_on_redelivery(self, pending_payment):
        """Duas entregas do mesmo evento RECEIVED não devem quebrar nem sobrescrever payment_date."""
        first = process_asaas_webhook({"payment": {"id": pending_payment.asaas_payment_id, "status": "RECEIVED"}})
        first_payment_date = first.payment_date

        second = process_asaas_webhook({"payment": {"id": pending_payment.asaas_payment_id, "status": "RECEIVED"}})

        assert second.payment_date == first_payment_date
        scheduling = Scheduling.objects.get(pk=pending_payment.scheduling_id)
        assert scheduling.status == Scheduling.SchedulingStatus.CONFIRMED


# ═══════════════════════════════════════════════════════════════════════════════
# refund_payment
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestRefundPayment:
    def test_payment_not_found_raises(self):
        import uuid
        with pytest.raises(PaymentNotFound):
            refund_payment(payment_id=uuid.uuid4())

    def test_boleto_is_not_refundable(self, pending_payment):
        pending_payment.billing_type = Payment.PaymentMode.BOLETO
        pending_payment.status = Payment.PaymentStatus.RECEIVED
        pending_payment.save(update_fields=["billing_type", "status"])

        with pytest.raises(PaymentNotRefundable):
            refund_payment(payment_id=pending_payment.id)

    def test_status_not_refundable(self, pending_payment):
        # ainda PENDING — não foi pago, não há o que estornar
        with pytest.raises(PaymentNotRefundable):
            refund_payment(payment_id=pending_payment.id)

    def test_value_greater_than_payment_value_raises(self, pending_payment):
        pending_payment.status = Payment.PaymentStatus.RECEIVED
        pending_payment.save(update_fields=["status"])

        with pytest.raises(PaymentNotRefundable):
            refund_payment(payment_id=pending_payment.id, value=Decimal("999.00"))

    @patch("beauty_formula.apps.payment.services.payment_service.AsaasClient")
    def test_successful_full_refund(self, asaas_client_cls, pending_payment):
        pending_payment.status = Payment.PaymentStatus.RECEIVED
        pending_payment.save(update_fields=["status"])

        asaas_client_cls.return_value.refund_payment.return_value = {"status": "REFUNDED"}

        result = refund_payment(payment_id=pending_payment.id)

        assert result.status == Payment.PaymentStatus.REFUNDED
        asaas_client_cls.return_value.refund_payment.assert_called_once_with(
            pending_payment.asaas_payment_id, value=None, description=None,
        )


# ═══════════════════════════════════════════════════════════════════════════════
# create_charge_for_scheduling
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestCreateChargeForScheduling:
    def test_scheduling_already_has_active_payment_raises(self, pending_payment):
        with pytest.raises(SchedulingAlreadyPaid):
            create_charge_for_scheduling(scheduling=pending_payment.scheduling, billing_type=Payment.PaymentMode.PIX)

    @patch("beauty_formula.apps.payment.services.payment_service.send_payment_request")
    @patch("beauty_formula.apps.payment.services.payment_service.AsaasClient")
    def test_successful_pix_charge_fetches_qrcode_and_queues_email(self, asaas_client_cls, send_email_task, scheduling):
        instance = asaas_client_cls.return_value
        instance.create_payment.return_value = {
            "id": "pay_new",
            "billingType": "PIX",
            "value": 100.0,
            "status": "PENDING",
            "invoiceUrl": "https://asaas.example/invoice",
            "bankSlipUrl": None,
            "netValue": 97.0,
        }
        instance.get_pix_qrcode.return_value = {"encodedImage": "img_b64", "payload": "00020126..."}

        payment = create_charge_for_scheduling(scheduling=scheduling, billing_type=Payment.PaymentMode.PIX)

        assert payment.asaas_payment_id == "pay_new"
        assert payment.pix_qr_code == "img_b64"
        assert payment.pix_copy_paste == "00020126..."
        send_email_task.delay.assert_called_once()

    @patch("beauty_formula.apps.payment.services.payment_service.AsaasClient")
    def test_credit_card_without_cpf_cnpj_raises(self, asaas_client_cls, scheduling):
        with pytest.raises(CpfOrCnpjRequired):
            create_charge_for_scheduling(scheduling=scheduling, billing_type=Payment.PaymentMode.CREDIT_CARD)

        # Sem CPF/CNPJ o fluxo tem que falhar antes de qualquer chamada à Asaas.
        asaas_client_cls.return_value.create_payment.assert_not_called()

    @patch("beauty_formula.apps.payment.services.payment_service.create_payment")
    @patch("beauty_formula.apps.payment.services.payment_service.AsaasClient")
    def test_local_persist_failure_triggers_compensating_cancel_on_asaas(
        self, asaas_client_cls, create_payment_repo, scheduling
    ):
        """
        A cobrança já foi criada na Asaas quando a persistência local
        falha (ex: erro de banco) — o rollback tem que cancelar essa
        cobrança órfã na Asaas em vez de deixá-la pendurada.
        """
        instance = asaas_client_cls.return_value
        instance.create_payment.return_value = {
            "id": "pay_orfa",
            "billingType": "PIX",
            "value": 100.0,
            "status": "PENDING",
        }
        create_payment_repo.side_effect = Exception("falha de banco simulada")

        with pytest.raises(Exception, match="falha de banco simulada"):
            create_charge_for_scheduling(scheduling=scheduling, billing_type=Payment.PaymentMode.PIX)

        instance.cancel_payment.assert_called_once_with("pay_orfa")

    @patch("beauty_formula.apps.payment.services.payment_service.create_payment")
    @patch("beauty_formula.apps.payment.services.payment_service.AsaasClient")
    def test_local_persist_failure_when_compensating_cancel_also_fails_still_raises_original(
        self, asaas_client_cls, create_payment_repo, scheduling
    ):
        """
        Cenário de pior caso: nem o cancelamento compensatório funciona.
        Precisa de reconciliação manual — mas o erro original (o que
        causou a falha de persistência) é o que deve subir, não o erro
        do cancelamento.
        """
        instance = asaas_client_cls.return_value
        instance.create_payment.return_value = {"id": "pay_orfa", "billingType": "PIX", "value": 100.0, "status": "PENDING"}
        instance.cancel_payment.side_effect = AsaasAPIError("Asaas fora do ar")
        create_payment_repo.side_effect = Exception("falha de banco simulada")

        with pytest.raises(Exception, match="falha de banco simulada"):
            create_charge_for_scheduling(scheduling=scheduling, billing_type=Payment.PaymentMode.PIX)


# ═══════════════════════════════════════════════════════════════════════════════
# cancel_payment_for_scheduling
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestCancelPaymentForScheduling:
    def test_no_active_payment_is_noop(self, scheduling):
        # não levanta, não faz nada — não há cobrança pra cancelar
        cancel_payment_for_scheduling(scheduling.id)

    def test_already_paid_payment_is_not_touched(self, pending_payment):
        pending_payment.status = Payment.PaymentStatus.RECEIVED
        pending_payment.save(update_fields=["status"])

        cancel_payment_for_scheduling(pending_payment.scheduling_id)

        pending_payment.refresh_from_db()
        assert pending_payment.status == Payment.PaymentStatus.RECEIVED

    @patch("beauty_formula.apps.payment.services.payment_service.AsaasClient")
    def test_pending_payment_is_cancelled_on_asaas_and_locally(self, asaas_client_cls, pending_payment):
        cancel_payment_for_scheduling(pending_payment.scheduling_id)

        asaas_client_cls.return_value.cancel_payment.assert_called_once_with(pending_payment.asaas_payment_id)
        pending_payment.refresh_from_db()
        assert pending_payment.status == Payment.PaymentStatus.CANCELLED

    @patch("beauty_formula.apps.payment.services.payment_service.AsaasClient")
    def test_asaas_failure_does_not_raise_and_leaves_status_untouched(self, asaas_client_cls, pending_payment):
        """
        Cancelamento do agendamento não pode travar por causa de uma
        chamada externa instável — só loga e segue. A cobrança fica
        "órfã" (ainda PENDING localmente) pra reconciliação manual.
        """
        asaas_client_cls.return_value.cancel_payment.side_effect = AsaasAPIError("Asaas fora do ar")

        cancel_payment_for_scheduling(pending_payment.scheduling_id)  # não deve levantar

        pending_payment.refresh_from_db()
        assert pending_payment.status == Payment.PaymentStatus.PENDING


# ═══════════════════════════════════════════════════════════════════════════════
# sync_payment_with_asaas
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestSyncPaymentWithAsaas:
    def test_payment_not_found_raises(self):
        import uuid
        with pytest.raises(PaymentNotFound):
            sync_payment_with_asaas(uuid.uuid4())

    @patch("beauty_formula.apps.payment.services.payment_service.AsaasClient")
    def test_pulls_status_from_asaas_and_confirms_scheduling(self, asaas_client_cls, pending_payment):
        asaas_client_cls.return_value.get_payment.return_value = {"status": "RECEIVED"}

        result = sync_payment_with_asaas(pending_payment.id)

        assert result.status == Payment.PaymentStatus.RECEIVED
        scheduling = Scheduling.objects.get(pk=pending_payment.scheduling_id)
        assert scheduling.status == Scheduling.SchedulingStatus.CONFIRMED