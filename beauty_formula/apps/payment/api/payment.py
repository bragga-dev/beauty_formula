"""
Rotas de Payment (Cobranças via Asaas).

- Cliente: gera a cobrança do próprio agendamento e consulta as próprias.
- Admin: visão total, com filtros.
- Webhook: endpoint público (sem JWT) validado pelo token configurado no
  painel do Asaas — é o Asaas quem chama isso, não o front.
"""
import hmac
from uuid import UUID

from django.conf import settings
from django.http import HttpRequest
from django_ratelimit.decorators import ratelimit
from ninja import Router

from beauty_formula.apps.accounts.models.user import User
from beauty_formula.apps.accounts.schemas.user_schema import MessageOut
from beauty_formula.apps.core.exceptions.payment_exception import (
    AsaasAPIError,
    PaymentNotFound,
    SchedulingAlreadyPaid,
    CpfOrCnpjRequired,
)
from beauty_formula.apps.core.exceptions.permissions import ClientNotFoundError
from beauty_formula.apps.core.exceptions.service_exception import SchedulingNotFound
from beauty_formula.apps.core.permissions.auth_classes import AdminOnlyAuth, ClientOnlyAuth
from beauty_formula.apps.core.utils.pagination import PAGE_SIZE_DEFAULT, PageOut, paginate_queryset
from beauty_formula.apps.payment.schemas.payment_schema import (
    PaymentCreateSchema,
    PaymentFilterSchema,
    PaymentResponseSchema,
)
from beauty_formula.apps.payment.selectors.payment_selector import filter_payments, get_payments_by_client
from beauty_formula.apps.payment.services.payment_service import (
    create_charge_for_client,
    get_own_payment_detail,
    process_asaas_webhook,
)

router = Router()


# ═══════════════════════════════════════════════════════════════════════════════
# Cliente
# ═══════════════════════════════════════════════════════════════════════════════

@router.post(
    "/create-charge",
    response={201: PaymentResponseSchema, 400: MessageOut, 404: MessageOut},
    auth=ClientOnlyAuth(),
    summary="Cliente gera a cobrança do próprio agendamento",
)
@ratelimit(key="user", rate="10/m", block=True)
def create_charge_router(request, payload: PaymentCreateSchema):
    user: User = request.auth
    try:
        payment = create_charge_for_client(
            user_id=user.id,
            scheduling_id=payload.scheduling_id,
            billing_type=payload.billing_type.value,
            cpf_cnpj=payload.cpf_cnpj,
        )
        return 201, PaymentResponseSchema.from_orm(payment)
    except ClientNotFoundError:
        return 404, {"detail": "Cliente não encontrado."}
    except SchedulingNotFound:
        return 404, {"detail": "Agendamento não encontrado."}
    except SchedulingAlreadyPaid as e:
        return 400, {"detail": str(e)}
    except CpfOrCnpjRequired as e:
        return 400, {"detail": str(e)}
    except AsaasAPIError as e:
        return 400, {"detail": e.message}

@router.get(
    "/my-payments",
    response={200: PageOut[PaymentResponseSchema], 404: MessageOut},
    auth=ClientOnlyAuth(),
    summary="Cliente lista as próprias cobranças",
)
def list_my_payments_router(request, page: int = 1, page_size: int = PAGE_SIZE_DEFAULT):
    user: User = request.auth
    from beauty_formula.apps.accounts.selectors.client_selector import get_client_by_user_id

    client = get_client_by_user_id(user.id)
    if client is None:
        return 404, {"detail": "Cliente não encontrado."}

    payments_qs = get_payments_by_client(client.id)
    result = paginate_queryset(payments_qs, page, page_size, PaymentResponseSchema.from_orm)
    return 200, result


@router.get(
    "/my-payments/{payment_id}",
    response={200: PaymentResponseSchema, 404: MessageOut},
    auth=ClientOnlyAuth(),
    summary="Cliente vê o detalhe de uma cobrança própria",
)
def get_my_payment_router(request, payment_id: UUID):
    user: User = request.auth
    try:
        payment = get_own_payment_detail(user_id=user.id, payment_id=payment_id)
        return 200, PaymentResponseSchema.from_orm(payment)
    except (ClientNotFoundError, PaymentNotFound):
        return 404, {"detail": "Cobrança não encontrada."}


# ═══════════════════════════════════════════════════════════════════════════════
# Admin
# ═══════════════════════════════════════════════════════════════════════════════

@router.get(
    "/list-all",
    response={200: PageOut[PaymentResponseSchema]},
    auth=AdminOnlyAuth(),
    summary="Admin lista todas as cobranças, com filtros",
)
def list_all_payments_router(request, filters: PaymentFilterSchema = ..., page: int = 1, page_size: int = PAGE_SIZE_DEFAULT):
    payments_qs = filter_payments(
        client_id=filters.client_id,
        status=filters.status.value if filters.status else None,
        billing_type=filters.billing_type.value if filters.billing_type else None,
        start_date=filters.start_date,
        end_date=filters.end_date,
        synced=filters.synced,
    )
    result = paginate_queryset(payments_qs, page, page_size, PaymentResponseSchema.from_orm)
    return 200, result


# ═══════════════════════════════════════════════════════════════════════════════
# Webhook Asaas — SEM JWT. Autenticado pelo token do header, não por usuário.
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/webhook", response={200: dict, 401: dict}, auth=None, summary="Webhook do Asaas")
def asaas_webhook_router(request: HttpRequest):
    received_token = request.headers.get("asaas-access-token", "")
    expected_token = settings.ASAAS_WEBHOOK_TOKEN

    if not expected_token or not hmac.compare_digest(received_token, expected_token):
        return 401, {"detail": "Token de webhook inválido."}

    import json
    payload = json.loads(request.body)

    try:
        process_asaas_webhook(payload)
    except PaymentNotFound:
        # Não achar o payment local não é erro do Asaas — devolve 200 pra
        # ele não ficar reenviando o evento em loop.
        pass

    return 200, {"received": True}