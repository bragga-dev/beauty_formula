from django.conf import settings
from django.utils import timezone

from beauty_formula.apps.services.models.scheduling import Scheduling
from beauty_formula.apps.payment.models.payment_model import Payment
from beauty_formula.apps.payment.integrations.asaas_client import AsaasClient
from beauty_formula.apps.payment.repositories import payment_repository
from beauty_formula.apps.payment.selectors import payment_selector
from beauty_formula.apps.core.exceptions.payment_exception import SchedulingAlreadyPaid


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