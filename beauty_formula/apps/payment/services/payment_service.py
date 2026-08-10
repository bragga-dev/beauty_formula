from datetime import timedelta

from django.conf import settings
from django.utils import timezone

from beauty_formula.apps.accounts.selectors.client_selector import get_client_by_user_id
from beauty_formula.apps.core.exceptions.permissions import ClientNotFoundError
from beauty_formula.apps.payment.models.payment_model import Payment
from beauty_formula.apps.payment.integrations.asaas_client import AsaasClient
from beauty_formula.apps.payment.repositories import payment_repository
from beauty_formula.apps.payment.selectors import payment_selector
from beauty_formula.apps.core.exceptions.payment_exception import SchedulingAlreadyPaid, PaymentNotFound
from beauty_formula.apps.core.exceptions.service_exception import SchedulingNotFound
from beauty_formula.apps.services.models.scheduling import Scheduling
from beauty_formula.apps.services.selectors.scheduling_selector import get_scheduling_by_id


def create_charge_for_scheduling(scheduling: Scheduling, billing_type: str) -> Payment:
    """
    Cria a cobrança na Asaas pro valor do agendamento (price_at_booking) e
    persiste o Payment local via payment_repository.

    Não existe customer por cliente: toda cobrança do sistema usa o mesmo
    ASAAS_CUSTOMER_ID (o customer único, criado uma vez pelo dono da
    barbearia). O agendamento/cliente real fica só no seu banco — a Asaas
    recebe apenas `externalReference` (id do agendamento) e a descrição.

    Se billing_type for PIX, já busca o QR Code na sequência.
    """
    if payment_selector.get_active_payment_for_scheduling(scheduling.id) is not None:
        raise SchedulingAlreadyPaid()

    asaas = AsaasClient()

    due_days = getattr(settings, "ASAAS_PAYMENT_DUE_DAYS", 1)
    due_date = timezone.now().date() + timedelta(days=due_days)

    description = f"{scheduling.service.name} - {scheduling.client.get_full_name()} - {scheduling.scheduled_time.strftime('%d/%m/%Y %H:%M')}"

    response = asaas.create_payment(
        customer_id=settings.ASAAS_CUSTOMER_ID,
        billing_type=billing_type,
        value=scheduling.price_at_booking,
        due_date=due_date.isoformat(),
        description=description,
        external_reference=str(scheduling.id),
    )

    payment = payment_repository.create_payment(
        scheduling=scheduling,
        client=scheduling.client,
        billing_type=response["billingType"],
        value=response["value"],
        due_date=due_date,
        description=description,
        asaas_payment_id=response["id"],
        asaas_customer_id=settings.ASAAS_CUSTOMER_ID,
        status=response["status"],
        external_reference=str(scheduling.id),
        invoice_url=response.get("invoiceUrl"),
        bank_slip_url=response.get("bankSlipUrl"),
        net_value=response.get("netValue"),
    )

    if billing_type == Payment.PaymentMode.PIX:
        qrcode = asaas.get_pix_qrcode(payment.asaas_payment_id)
        payment = payment_repository.attach_pix_data(
            payment,
            pix_qr_code=qrcode.get("encodedImage"),
            pix_copy_paste=qrcode.get("payload"),
        )

    return payment


def create_charge_for_client(*, user_id, scheduling_id, billing_type: str) -> Payment:
    """Wrapper com checagem de posse: cliente só cobra o próprio agendamento."""
    client = get_client_by_user_id(user_id)
    if client is None:
        raise ClientNotFoundError()

    scheduling = get_scheduling_by_id(scheduling_id)
    if scheduling is None or scheduling.client_id != client.id:
        raise SchedulingNotFound()

    return create_charge_for_scheduling(scheduling, billing_type)


def get_own_payment_detail(*, user_id, payment_id) -> Payment:
    client = get_client_by_user_id(user_id)
    if client is None:
        raise ClientNotFoundError()

    payment = payment_selector.get_payment_by_id(payment_id)
    if payment is None or payment.client_id != client.id:
        raise PaymentNotFound()

    return payment


def process_asaas_webhook(payload: dict) -> Payment:
    """
    Aplica o status vindo do webhook do Asaas. O payload já traz o objeto
    `payment` completo com `status` atualizado — não precisamos reconstruir
    o status a partir do nome do evento (`event`), só usar o que já veio.
    """
    payment_data = payload.get("payment") or {}
    asaas_payment_id = payment_data.get("id")
    status = payment_data.get("status")

    if not asaas_payment_id or not status:
        raise PaymentNotFound("Payload de webhook sem id ou status de pagamento.")

    payment = payment_selector.get_payment_by_asaas_id(asaas_payment_id)
    if payment is None:
        raise PaymentNotFound()

    return payment_repository.update_payment_status(payment, status=status)