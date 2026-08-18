"""
Repository de Payment — funções de persistência (criação, atualização de
status e sincronização com a Asaas).

Como no scheduling_repository, essas funções recebem valores já resolvidos
(instância de Scheduling/Client, não IDs) e dados já normalizados vindos
da resposta da Asaas — resolver `scheduling_id` pra instância e montar a
chamada pra Asaas é responsabilidade do payment_service, não daqui.
"""
from decimal import Decimal
from typing import Optional
from uuid import UUID

from django.db import transaction
from django.utils import timezone

from beauty_formula.apps.accounts.models.client import Client
from beauty_formula.apps.payment.models.payment_model import Payment
from beauty_formula.apps.services.models.scheduling import Scheduling


@transaction.atomic
def create_payment(
    *,
    scheduling: Scheduling,
    client: Client,
    billing_type: str,
    value: Decimal,
    due_date,
    description: str,
    asaas_payment_id: str,
    asaas_customer_id: str,
    status: str = Payment.PaymentStatus.PENDING,
    external_reference: Optional[str] = None,
    invoice_url: Optional[str] = None,
    bank_slip_url: Optional[str] = None,
    net_value: Optional[Decimal] = None,
) -> Payment:
    """Persiste localmente uma cobrança já criada na Asaas."""
    return Payment.objects.create(
        scheduling=scheduling,
        client=client,
        billing_type=billing_type,
        value=value,
        due_date=due_date,
        description=description,
        asaas_payment_id=asaas_payment_id,
        asaas_customer_id=asaas_customer_id,
        status=status,
        external_reference=external_reference,
        invoice_url=invoice_url,
        bank_slip_url=bank_slip_url,
        net_value=net_value,
        synced_with_asaas=True,
    )


@transaction.atomic
def attach_pix_data(payment: Payment, *, pix_qr_code: str, pix_copy_paste: str) -> Payment:
    """Grava o QR Code/copia-e-cola retornados pelo endpoint de Pix da Asaas."""
    payment.pix_qr_code = pix_qr_code
    payment.pix_copy_paste = pix_copy_paste
    payment.save(update_fields=["pix_qr_code", "pix_copy_paste", "updated_at"])
    return payment


@transaction.atomic
def update_payment_status(payment: Payment, *, status: str, payment_date=None) -> Payment:
    """
    Aplica uma mudança de status vinda do webhook da Asaas (PAYMENT_RECEIVED,
    PAYMENT_CONFIRMED, PAYMENT_OVERDUE, etc.).
    """
    update_fields = ["status", "updated_at", "synced_with_asaas"]
    payment.status = status
    payment.synced_with_asaas = True

    if status in {Payment.PaymentStatus.RECEIVED, Payment.PaymentStatus.CONFIRMED} and payment.payment_date is None:
        payment.payment_date = payment_date or timezone.now()
        update_fields.append("payment_date")

    payment.save(update_fields=update_fields)
    return payment


@transaction.atomic
def mark_payment_out_of_sync(payment: Payment) -> Payment:
    """Marca que a cobrança pode estar desatualizada em relação à Asaas (ex: falha ao processar um webhook)."""
    payment.synced_with_asaas = False
    payment.save(update_fields=["synced_with_asaas", "updated_at"])
    return payment


@transaction.atomic
def delete_payment(payment: Payment) -> None:
    """
    Exclui o registro local do pagamento. Não cancela a cobrança na Asaas
    — se for o caso, cancele lá primeiro (AsaasClient.cancel_payment) antes
    de chamar isso.
    """
    payment.delete()