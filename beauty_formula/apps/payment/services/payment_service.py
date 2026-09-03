import logging
from datetime import timedelta
from typing import Optional
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
    CpfOrCnpjRequired,
    PaymentNotRefundable,
    
)
from beauty_formula.apps.payment.tasks.send_payment_request import send_payment_request
from beauty_formula.apps.core.exceptions.service_exception import SchedulingNotFound, SchedulingConflict
from beauty_formula.apps.services.models.scheduling import Scheduling
from beauty_formula.apps.services.selectors.scheduling_selector import get_scheduling_by_id
from beauty_formula.apps.accounts.repositories.client_repository import (
    set_client_asaas_customer_id,
)
from beauty_formula.apps.core.validators.validate_cpf_cnpj import validate_cpf_or_cnpj

_REFUNDABLE_STATUSES = {Payment.PaymentStatus.RECEIVED, Payment.PaymentStatus.CONFIRMED}
_PAID_PAYMENT_STATUSES = {Payment.PaymentStatus.RECEIVED, Payment.PaymentStatus.CONFIRMED}

logger = logging.getLogger(__name__)

def _resolve_asaas_customer_id(scheduling: Scheduling, billing_type: str, cpf_cnpj: Optional[str] | None, asaas: AsaasClient) -> str:
    """
    PIX/Boleto: sempre o customer único do dono do salão (settings.ASAAS_CUSTOMER_ID)
    — nenhum dado do cliente vai pra Asaas além do externalReference.

    Cartão de crédito: customer PRÓPRIO do cliente, porque a fatura da Asaas
    mostra os dados do customer vinculado como "Dados do comprador" — usando
    o customer do salão, o pagador via os dados do salão em vez dos dele.
    Criado uma vez (exige CPF/CNPJ, obrigatório na API da Asaas) e salvo em
    client.asaas_customer_id pra não pedir de novo nas próximas cobranças.
    """
    if billing_type != Payment.PaymentMode.CREDIT_CARD:
        return settings.ASAAS_CUSTOMER_ID

    client = scheduling.client
    if client.asaas_customer_id:
        return client.asaas_customer_id

    if not cpf_cnpj:
        raise CpfOrCnpjRequired()
    
    validate_cpf_or_cnpj(cpf_cnpj)

    response = asaas.create_customer(
        name=client.get_full_name(),
        cpf_cnpj=cpf_cnpj,
        email=client.user.email,
        external_reference=str(client.id),
    )
    set_client_asaas_customer_id(client=client, asaas_customer_id=response["id"])
    return response["id"]



def create_charge_for_scheduling(scheduling: Scheduling, billing_type: str, cpf_cnpj: str | None = None) -> Payment:
    if get_active_payment_for_scheduling(scheduling.id) is not None:
        raise SchedulingAlreadyPaid()

    asaas = AsaasClient()

    customer_id = _resolve_asaas_customer_id(scheduling=scheduling, billing_type=billing_type, cpf_cnpj=cpf_cnpj, asaas=asaas)

    due_days = getattr(settings, "ASAAS_PAYMENT_DUE_DAYS", 1)
    due_date = timezone.now().date() + timedelta(days=due_days)

    description = f"{scheduling.service.name} - {scheduling.client.get_full_name()} - {scheduling.scheduled_time.strftime('%d/%m/%Y %H:%M')}"

    response = asaas.create_payment(
        customer_id=customer_id,
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
            payment = mark_payment_out_of_sync(payment)
    send_payment_request.delay(user_id=scheduling.client.user.id, payment_id=payment.id)
    return payment


def create_charge_for_client(*, user_id, scheduling_id, billing_type: str, cpf_cnpj: str | None = None) -> Payment:
    client = get_client_by_user_id(user_id=user_id)
    if client is None:
        raise ClientNotFoundError()

    scheduling = get_scheduling_by_id(scheduling_id=scheduling_id)
    if scheduling is None or scheduling.client_id != client.id:
        raise SchedulingNotFound()

    return create_charge_for_scheduling(scheduling=scheduling, billing_type=billing_type, cpf_cnpj=cpf_cnpj)



def sync_payment_with_asaas(payment_id) -> Payment:
    """
    Puxa o estado atual da cobrança direto da Asaas e atualiza o registro
    local — fallback manual pra quando o webhook atrasa ou falha (a
    reentrega da Asaas não é infinita). Uso do admin, numa cobrança que
    parece travada em PENDING no painel.
    """
    payment = get_payment_by_id(payment_id=payment_id)
    if payment is None:
        raise PaymentNotFound()

    response = AsaasClient().get_payment(payment_id=payment.asaas_payment_id)
    payment = update_payment_status(payment=payment, status=response["status"])
    _confirm_scheduling_if_paid(payment)
    return payment


def refund_payment(*, payment_id, value=None, description: str | None = None) -> Payment:
    """
    Estorno manual, acionado pelo admin (nunca automático — cancelamento
    de agendamento não estorna sozinho, ver cancel_payment_for_scheduling).

    Só cobre Pix e cartão de crédito já RECEIVED/CONFIRMED. Boleto tem
    fluxo próprio na Asaas (exige dados bancários do pagador) — fora de
    escopo aqui.

    value None = estorno integral. value informado = estorno parcial
    (ex: reter taxa de cancelamento); a Asaas quem valida se cabe no
    saldo disponível da cobrança, considerando estornos parciais
    anteriores — não replicamos essa conta aqui, só a validação óbvia
    (não deixar mandar mais que o valor total da cobrança).
    """
    payment = get_payment_by_id(payment_id=payment_id)
    if payment is None:
        raise PaymentNotFound()

    if payment.billing_type == Payment.PaymentMode.BOLETO:
        raise PaymentNotRefundable("Estorno de boleto exige dados bancários do cliente — não suportado por aqui.")

    if payment.status not in _REFUNDABLE_STATUSES:
        raise PaymentNotRefundable()

    if value is not None and value > payment.value:
        raise PaymentNotRefundable("Valor do estorno não pode ser maior que o valor da cobrança.")

    response = AsaasClient().refund_payment(
        payment.asaas_payment_id,
        value=float(value) if value is not None else None,
        description=description,
    )

    return update_payment_status(payment=payment, status=response["status"])


def get_own_payment_detail(*, user_id, payment_id) -> Payment:
    client = get_client_by_user_id(user_id=user_id)
    if client is None:
        raise ClientNotFoundError()

    payment = get_payment_by_id(payment_id=payment_id)
    if payment is None or payment.client_id != client.id:
        raise PaymentNotFound()
    return payment




def _confirm_scheduling_if_paid(payment: Payment) -> None:
    """
    Se o pagamento acabou de virar RECEIVED/CONFIRMED, confirma o
    agendamento vinculado (CREATED -> CONFIRMED).

    Import local pra evitar import circular: scheduling_service já
    importa deste módulo (`cancel_payment_for_scheduling`) no nível do
    módulo, então importar scheduling_service aqui em cima criaria um
    ciclo.

    Nunca deixa uma falha de confirmação derrubar o processamento do
    pagamento em si (webhook precisa responder 200 rápido pra Asaas não
    ficar reentregando) — só loga pra reconciliação manual. O caso mais
    provável de falhar aqui é `SchedulingConflict`: o horário foi
    ocupado por outro agendamento confirmado enquanto este esperava
    pagamento — dinheiro recebido, mas o horário já era. Cancela a
    reserva perdedora automaticamente (não mexe no pagamento) e notifica
    o admin por e-mail — o estorno em si continua manual
    (`refund_payment`), de propósito.
    """
    if payment.status not in _PAID_PAYMENT_STATUSES:
        return

    from beauty_formula.apps.services.services.scheduling_service import (
        cancel_scheduling_due_to_payment_conflict,
        confirm_scheduling_after_payment,
    )
    from beauty_formula.apps.payment.tasks.send_scheduling_payment_conflict_admin_notification import (
        send_scheduling_payment_conflict_admin_notification,
    )

    try:
        confirm_scheduling_after_payment(scheduling_id=payment.scheduling_id)
    except SchedulingConflict:
        logger.error(
            "Pagamento %s recebido mas o agendamento %s não pôde ser confirmado "
            "(horário não está mais disponível) — requer estorno manual e "
            "reconciliação com o cliente.",
            payment.id, payment.scheduling_id,
        )
        cancel_scheduling_due_to_payment_conflict(scheduling_id=payment.scheduling_id)
        send_scheduling_payment_conflict_admin_notification.delay(payment_id=payment.id)


def process_asaas_webhook(payload: dict) -> Payment:
    """
    Aplica o status vindo do webhook do Asaas. O payload já traz o objeto
    `payment` completo com `status` atualizado — não precisamos reconstruir
    o status a partir do nome do evento (`event`), só usar o que já veio.

    Quando o novo status indica pagamento recebido, confirma o agendamento
    vinculado (ver `_confirm_scheduling_if_paid`) — é isso que efetiva a
    transição CREATED -> CONFIRMED no fluxo normal.
    """
    payment_data = payload.get("payment") or {}
    asaas_payment_id = payment_data.get("id")
    status = payment_data.get("status")

    if not asaas_payment_id or not status:
        raise PaymentNotFound("Payload de webhook sem id ou status de pagamento.")

    payment = get_payment_by_asaas_id(asaas_payment_id=asaas_payment_id)
    if payment is None:
        raise PaymentNotFound()

    payment = update_payment_status(payment=payment, status=status)
    _confirm_scheduling_if_paid(payment)
    return payment


def cancel_payment_for_scheduling(scheduling_id) -> None:
    """
    Cancela na Asaas a cobrança pendente vinculada ao agendamento, se
    existir. Chamada pelo scheduling_service sempre que um agendamento é
    cancelado (cliente, funcionário ou admin) — evita deixar uma cobrança
    PENDING pendurada pra um serviço que não vai mais acontecer.

    Se a cobrança já foi paga (RECEIVED/CONFIRMED), não mexe nela aqui —
    a Asaas não permite excluir cobrança já paga; devolver o dinheiro é
    caso de estorno (endpoint futuro), não de cancelamento.

    Falha de comunicação com a Asaas NÃO impede o cancelamento do
    agendamento: só loga o erro. Travar o cancelamento do cliente por
    causa de uma chamada externa instável seria pior que deixar uma
    cobrança órfã pra resolver depois manualmente.
    """
    payment = get_active_payment_for_scheduling(scheduling_id)
    if payment is None or payment.status != Payment.PaymentStatus.PENDING:
        return

    try:
        AsaasClient().cancel_payment(payment.asaas_payment_id)
    except AsaasAPIError:
        logger.exception(
            "Falha ao cancelar cobrança %s na Asaas (agendamento %s) — "
            "agendamento foi cancelado normalmente mesmo assim.",
            payment.asaas_payment_id, scheduling_id,
        )
        return

    update_payment_status(payment, status=Payment.PaymentStatus.CANCELLED)