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
    CpfOrCnpjRequired,
)
from beauty_formula.apps.core.exceptions.service_exception import SchedulingNotFound
from beauty_formula.apps.services.models.scheduling import Scheduling
from beauty_formula.apps.services.selectors.scheduling_selector import get_scheduling_by_id
from beauty_formula.apps.accounts.repositories.client_repository import (
    set_client_asaas_customer_id,
)
from beauty_formula.apps.core.validators.validate_cpf_cnpj import validate_cnpj, validate_cpf


logger = logging.getLogger(__name__)

def _resolve_asaas_customer_id(scheduling: Scheduling, billing_type: str, cpf_cnpj: str | None, asaas: AsaasClient) -> str:
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
    
    if not validate_cpf(value=cpf_cnpj) or not validate_cnpj(value=cpf_cnpj):
        raise  CpfOrCnpjRequired("CPF ou CNPJ inválido!")


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


def create_charge_for_client(*, user_id, scheduling_id, billing_type: str, cpf_cnpj: str | None = None) -> Payment:
    client = get_client_by_user_id(user_id=user_id)
    if client is None:
        raise ClientNotFoundError()

    scheduling = get_scheduling_by_id(scheduling_id=scheduling_id)
    if scheduling is None or scheduling.client_id != client.id:
        raise SchedulingNotFound()

    return create_charge_for_scheduling(scheduling=scheduling, billing_type=billing_type, cpf_cnpj=cpf_cnpj)


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


