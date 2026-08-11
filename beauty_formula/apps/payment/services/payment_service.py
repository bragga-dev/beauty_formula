import logging
from datetime import timedelta

from django.conf import settings
from django.utils import timezone

from beauty_formula.apps.accounts.selectors.client_selector import (
    get_client_by_user_id,

    )
from beauty_formula.apps.core.exceptions.permissions import ClientNotFoundError
from beauty_formula.apps.payment.models.payment_model import Payment
from beauty_formula.apps.payment.integrations.asaas_client import AsaasClient
from beauty_formula.apps.payment.repositories.payment_repository import (
    create_payment,
    attach_pix_data,
    mark_payment_out_of_sync,
    update_payment_status,
    delete_payment,

)
from beauty_formula.apps.payment.selectors.payment_selector import (
    get_active_payment_for_scheduling,
    get_payment_by_id,
    get_payments_by_client,
    get_payment_by_asaas_id,
    get_payments_by_scheduling,

    )
from beauty_formula.apps.core.exceptions.payment_exception import (
    AsaasAPIError,
    SchedulingAlreadyPaid,
    PaymentNotFound,
)
from beauty_formula.apps.core.exceptions.service_exception import SchedulingNotFound
from beauty_formula.apps.services.models.scheduling import Scheduling
from beauty_formula.apps.services.selectors.scheduling_selector import get_scheduling_by_id

logger = logging.getLogger(__name__)


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
    if get_active_payment_for_scheduling(scheduling.id) is not None:
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

    try:
        payment = create_payment(
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
    except Exception:
        # A cobrança já existe na Asaas nesse ponto. Se não conseguirmos
        # persistir localmente (erro de banco, etc.), sem isso ela fica
        # órfã: cliente pode acabar pagando algo que o sistema não sabe
        # que existe, e get_active_payment_for_scheduling nunca vai achar
        # pra evitar duplicidade. Tenta cancelar na Asaas pra compensar;
        # se o cancelamento também falhar, ao menos loga pra reconciliação
        # manual em vez de mascarar o problema.
        try:
            asaas.cancel_payment(response["id"])
        except AsaasAPIError:
            logger.error(
                "Cobrança %s criada na Asaas mas não persistida localmente, "
                "e o cancelamento de compensação também falhou. Requer "
                "reconciliação manual.",
                response.get("id"),
            )
        raise

    if billing_type == Payment.PaymentMode.PIX:
        try:
            qrcode = asaas.get_pix_qrcode(payment.asaas_payment_id)
            payment = attach_pix_data(payment, pix_qr_code=qrcode.get("encodedImage"), pix_copy_paste=qrcode.get("payload"),)

        except AsaasAPIError:
            # A cobrança já foi criada na Asaas e já está persistida aqui —
            # não é caso de propagar o erro (isso já derrubaria a resposta
            # pro cliente com uma cobrança "fantasma": presa no banco sem
            # PIX, e sem chance de recriar por causa do
            # get_active_payment_for_scheduling). Só marca fora de sincronia
            # pra reconciliar depois (job/consulta posterior via
            # get_payment/get_pix_qrcode) e segue devolvendo a cobrança.
            payment = mark_payment_out_of_sync(payment)

    return payment


def create_charge_for_client(*, user_id, scheduling_id, billing_type: str) -> Payment:
    """Wrapper com checagem de posse: cliente só cobra o próprio agendamento."""
    client = get_client_by_user_id(user_id=user_id)
    if client is None:
        raise ClientNotFoundError()

    scheduling = get_scheduling_by_id(scheduling_id=scheduling_id)
    if scheduling is None or scheduling.client_id != client.id:
        raise SchedulingNotFound()

    return create_charge_for_scheduling(scheduling=scheduling, billing_type=billing_type)


def get_own_payment_detail(*, user_id, payment_id) -> Payment:
    client = get_client_by_user_id(user_id=user_id)
    if client is None:
        raise ClientNotFoundError()

    payment = get_payment_by_id(payment_id=payment_id)
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

    payment = get_payment_by_asaas_id(asaas_payment_id=asaas_payment_id)
    if payment is None:
        raise PaymentNotFound()

    return update_payment_status(payment=payment, status=status)