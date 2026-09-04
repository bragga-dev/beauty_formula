import logging
from datetime import timedelta
from decimal import Decimal
from typing import Optional
from django.conf import settings
from django.db import transaction
from django.utils import timezone

from beauty_formula.apps.accounts.models.user import User
from beauty_formula.apps.accounts.selectors.client_selector import (
    get_client_by_user_id,

    )
from beauty_formula.apps.core.exceptions.permissions import ClientNotFoundError
from beauty_formula.apps.payment.models.payment_model import Payment
from beauty_formula.apps.payment.models.refund_request_model import RefundRequest, DEFAULT_CANCELLATION_FEE_PERCENTAGE
from beauty_formula.apps.payment.integrations.asaas_client import AsaasClient
from beauty_formula.apps.payment.repositories.payment_repository import (
    create_payment,
    attach_pix_data,
    mark_payment_out_of_sync,
    update_payment_status,
    delete_payment,

)
from beauty_formula.apps.payment.repositories.refund_request_repository import (
    approve_refund_request as approve_refund_request_repo,
    create_refund_request,
    reject_refund_request as reject_refund_request_repo,
)
from beauty_formula.apps.payment.selectors.payment_selector import (
    get_active_payment_for_scheduling,
    get_payment_by_id,
    get_payments_by_client,
    get_payment_by_asaas_id,
    get_payments_by_scheduling,

    )
from beauty_formula.apps.payment.selectors.refund_request_selector import (
    get_pending_refund_request_for_payment,
    get_refund_request_by_id,
)
from beauty_formula.apps.core.exceptions.payment_exception import (
    AsaasAPIError,
    SchedulingAlreadyPaid,
    PaymentNotFound,
    CpfOrCnpjRequired,
    PaymentNotRefundable,
    RefundRequestAlreadyExists,
    RefundRequestAlreadyReviewed,
    RefundRequestNotFound,

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
    Estorno de fato na Asaas — acionado pelo admin, seja direto (endpoint
    de refund avulso) ou indiretamente ao aprovar um `RefundRequest`
    (`approve_refund_request_service`, que chama esta função com o valor
    já líquido da taxa de cancelamento). Nunca é chamado sozinho a partir
    de um cancelamento de agendamento — ver `cancel_payment_for_scheduling`,
    que só CRIA o pedido pra fila de análise, não estorna nada sem o
    admin decidir.

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
    ficar reentregando) — só loga pra reconciliação. O caso mais
    provável de falhar aqui é `SchedulingConflict`: o horário foi
    ocupado por outro agendamento confirmado enquanto este esperava
    pagamento — dinheiro recebido, mas o horário já era.
    `cancel_scheduling_due_to_payment_conflict` cancela a reserva
    perdedora E cria um `RefundRequest` (reembolso integral, taxa 0% —
    não é culpa do cliente) na mesma fila que qualquer outro pedido de
    reembolso — o admin vê e decide na mesma tela, não precisa de um
    e-mail avulso separado pra esse caso específico.
    """
    if payment.status not in _PAID_PAYMENT_STATUSES:
        return

    from beauty_formula.apps.services.services.scheduling_service import (
        cancel_scheduling_due_to_payment_conflict,
        confirm_scheduling_after_payment,
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


def cancel_payment_for_scheduling(scheduling_id, *, canceled_by: Optional[User] = None, reason: str = "") -> None:
    """
    Chamada pelo scheduling_service sempre que um agendamento é cancelado
    (cliente, funcionário ou admin) — trata a cobrança vinculada de dois
    jeitos bem diferentes dependendo do status dela:

    - PENDING (ainda não foi paga): cancela a cobrança na Asaas, mesmo
      comportamento de sempre. Não tem dinheiro envolvido, não precisa de
      análise de ninguém.

    - RECEIVED/CONFIRMED (já foi paga): NÃO estorna sozinho. Cria um
      `RefundRequest` na fila de análise do admin — é o admin quem decide
      acionar o estorno de verdade na Asaas (`approve_refund_request`),
      nunca automático. A taxa de cancelamento (10% por padrão) só se
      aplica quando é o próprio CLIENTE quem decide cancelar
      (`canceled_by.role == CLIENT`); cancelamento feito pelo salão
      (funcionário ou admin) gera pedido com taxa 0% — não é justo cobrar
      o cliente por uma decisão que não foi dele.

    Falha de comunicação com a Asaas (no caminho PENDING) NÃO impede o
    cancelamento do agendamento: só loga o erro. Travar o cancelamento do
    cliente por causa de uma chamada externa instável seria pior que
    deixar uma cobrança órfã pra resolver depois manualmente.
    """
    payment = get_active_payment_for_scheduling(scheduling_id)
    if payment is None:
        return

    if payment.status == Payment.PaymentStatus.PENDING:
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
        return

    if payment.status in _PAID_PAYMENT_STATUSES:
        _request_refund_for_paid_scheduling(payment, canceled_by=canceled_by, reason=reason)


def _request_refund_for_paid_scheduling(payment: Payment, *, canceled_by: Optional[User], reason: str) -> None:
    """
    Cria o RefundRequest e notifica o admin. Nunca deixa uma falha aqui
    (e-mail fora do ar, corrida rara de duplo cancelamento) derrubar o
    cancelamento do agendamento em si — o agendamento já foi cancelado
    antes desta função ser chamada, isso é só o rastro financeiro.
    """
    from beauty_formula.apps.payment.tasks.send_refund_request_admin_notification import (
        send_refund_request_admin_notification,
    )

    if get_pending_refund_request_for_payment(payment.id) is not None:
        logger.warning(
            "Já existe um RefundRequest pendente para o pagamento %s — não criou outro.", payment.id
        )
        return

    fee_percentage = (
        DEFAULT_CANCELLATION_FEE_PERCENTAGE
        if canceled_by is not None and canceled_by.role == User.UserRole.CLIENT
        else Decimal("0.00")
    )
    original_value = payment.value
    fee_value = (original_value * fee_percentage / Decimal("100")).quantize(Decimal("0.01"))
    refund_value = original_value - fee_value

    try:
        refund_request = create_refund_request(
            payment=payment,
            client=payment.client,
            requested_by=canceled_by or payment.client.user,
            reason=reason,
            original_value=original_value,
            fee_percentage=fee_percentage,
            fee_value=fee_value,
            refund_value=refund_value,
        )
    except RefundRequestAlreadyExists:
        logger.warning(
            "RefundRequest duplicado para o pagamento %s (corrida entre chamadas concorrentes) — ignorado.",
            payment.id,
        )
        return

    logger.info(
        "RefundRequest %s criado para pagamento %s: original=%s taxa=%s%% valor_a_devolver=%s",
        refund_request.id, payment.id, original_value, fee_percentage, refund_value,
    )
    send_refund_request_admin_notification.delay(refund_request_id=refund_request.id)


@transaction.atomic
def approve_refund_request_service(*, refund_request_id, reviewed_by: User, admin_notes: str = "") -> RefundRequest:
    """
    Aprovação do admin: aciona o estorno de verdade na Asaas
    (`refund_payment`, valor parcial = `refund_value`, já com a taxa
    descontada) e SÓ marca o pedido como APPROVED se a chamada à Asaas
    for bem-sucedida — se falhar, a exceção sobe (`PaymentNotRefundable`/
    `AsaasAPIError`) e o pedido continua PENDING, pronto pra tentar de
    novo, em vez de ficar com um status "aprovado" que não corresponde
    ao que realmente aconteceu no gateway de pagamento.
    """
    refund_request = get_refund_request_by_id(refund_request_id)
    if refund_request is None:
        raise RefundRequestNotFound()

    if refund_request.status != RefundRequest.RefundRequestStatus.PENDING:
        raise RefundRequestAlreadyReviewed()

    refund_payment(
        payment_id=refund_request.payment_id,
        value=refund_request.refund_value,
        description=f"Estorno aprovado (pedido {refund_request.id}) — taxa de {refund_request.fee_percentage}% retida.",
    )

    return approve_refund_request_repo(refund_request, reviewed_by=reviewed_by, admin_notes=admin_notes)


def reject_refund_request_service(*, refund_request_id, reviewed_by: User, admin_notes: str) -> RefundRequest:
    """Rejeição do admin — nenhum dinheiro é movimentado, o pagamento permanece como está."""
    refund_request = get_refund_request_by_id(refund_request_id)
    if refund_request is None:
        raise RefundRequestNotFound()

    if refund_request.status != RefundRequest.RefundRequestStatus.PENDING:
        raise RefundRequestAlreadyReviewed()

    return reject_refund_request_repo(refund_request, reviewed_by=reviewed_by, admin_notes=admin_notes)