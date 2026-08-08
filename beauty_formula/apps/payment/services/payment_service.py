from django.conf import settings
from django.utils import timezone
from beauty_formula.apps.services.models.scheduling import Scheduling
from beauty_formula.apps.payment.models.payment_model import Payment
from beauty_formula.apps.payment.integrations.asaas_client import AsaasClient
from beauty_formula.apps.core.exceptions.payment_exception import SchedulingAlreadyPaid

# Status que significam "essa cobrança ainda conta" — bloqueia criar outra pro mesmo agendamento.
_BLOCKING_STATUSES = {
    Payment.PaymentStatus.PENDING,
    Payment.PaymentStatus.RECEIVED,
    Payment.PaymentStatus.CONFIRMED,
}


def create_charge_for_scheduling(scheduling: Scheduling, billing_type: str) -> Payment:
    """
    Cria a cobrança na Asaas pro valor do agendamento (price_at_booking) e
    persiste o Payment local.

    Não existe customer por cliente: toda cobrança do sistema usa o mesmo
    ASAAS_CUSTOMER_ID (o customer único, criado uma vez pelo dono da
    barbearia). O agendamento/cliente real fica só no seu banco — a Asaas
    recebe apenas `externalReference` (id do agendamento) e a descrição.

    Se billing_type for PIX, já busca o QR Code na sequência.
    """
    already_charged = Payment.objects.filter(
        scheduling=scheduling,
        status__in=_BLOCKING_STATUSES,
    ).exists()
    if already_charged:
        raise SchedulingAlreadyPaid()

    asaas = AsaasClient()
    due_date = timezone.now().date()
    description = f"{scheduling.service.name} - {scheduling.client.get_full_name()} - {scheduling.scheduled_time.strftime('%d/%m/%Y %H:%M')}"

    response = asaas.create_payment(
        customer_id=settings.ASAAS_CUSTOMER_ID,
        billing_type=billing_type,
        value=scheduling.price_at_booking,
        due_date=due_date.isoformat(),
        description=description,
        external_reference=str(scheduling.id),
    )

    payment = Payment.objects.create(
        scheduling=scheduling,
        client=scheduling.client,
        asaas_payment_id=response["id"],
        asaas_customer_id=settings.ASAAS_CUSTOMER_ID,
        value=response["value"],
        billing_type=response["billingType"],
        status=response["status"],
        due_date=due_date,
        description=description,
        external_reference=str(scheduling.id),
        invoice_url=response.get("invoiceUrl"),
        bank_slip_url=response.get("bankSlipUrl"),
        net_value=response.get("netValue"),
        synced_with_asaas=True,
    )

    if billing_type == Payment.PaymentMode.PIX:
        _attach_pix_qrcode(payment, asaas)

    return payment


def _attach_pix_qrcode(payment: Payment, asaas: AsaasClient) -> Payment:
    qrcode = asaas.get_pix_qrcode(payment.asaas_payment_id)
    payment.pix_qr_code = qrcode.get("encodedImage")
    payment.pix_copy_paste = qrcode.get("payload")
    payment.save(update_fields=["pix_qr_code", "pix_copy_paste", "updated_at"])
    return payment