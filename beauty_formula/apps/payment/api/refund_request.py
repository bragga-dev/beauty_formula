"""
Rotas de RefundRequest (fila de análise de pedidos de reembolso).

- Admin: lista a fila (com filtro por status), vê o detalhe de um
  pedido, aprova (aciona o estorno de verdade na Asaas com o valor já
  líquido da taxa) ou rejeita (nenhum dinheiro se move).
- Cliente: só consulta o histórico dos PRÓPRIOS pedidos (sem escrita —
  o pedido é criado automaticamente pelo sistema quando ele cancela um
  agendamento já pago, não por uma ação direta dele aqui).
"""
from uuid import UUID
from typing import Optional

from django_ratelimit.decorators import ratelimit
from ninja import Router

from beauty_formula.apps.accounts.schemas.user_schema import MessageOut
from beauty_formula.apps.core.exceptions.payment_exception import (
    AsaasAPIError,
    PaymentNotRefundable,
    RefundRequestAlreadyReviewed,
    RefundRequestNotFound,
)
from beauty_formula.apps.core.permissions.auth_classes import AdminOnlyAuth, ClientOnlyAuth
from beauty_formula.apps.core.utils.pagination import PAGE_SIZE_DEFAULT, PageOut, paginate_queryset
from beauty_formula.apps.payment.schemas.refund_request_schema import (
    RefundRequestOut,
    RefundRequestReviewIn,
    RefundRequestStatusEnum,
)
from beauty_formula.apps.payment.selectors.refund_request_selector import (
    filter_refund_requests,
    get_refund_request_by_id,
    get_refund_requests_for_client,
)
from beauty_formula.apps.payment.services.payment_service import (
    approve_refund_request_service,
    reject_refund_request_service,
)
from beauty_formula.apps.accounts.selectors.client_selector import get_client_by_user_id

router = Router()


# ═══════════════════════════════════════════════════════════════════════════════
# Admin
# ═══════════════════════════════════════════════════════════════════════════════

@router.get(
    "/",
    response={200: PageOut[RefundRequestOut]},
    auth=AdminOnlyAuth(),
    summary="Admin lista a fila de pedidos de reembolso",
)
@ratelimit(key="user", rate="30/m", block=True)
def list_refund_requests_router(
    request, status: Optional[RefundRequestStatusEnum] = None, page: int = 1, page_size: int = PAGE_SIZE_DEFAULT
):
    qs = filter_refund_requests(status=status.value if status else None)
    result = paginate_queryset(qs, page, page_size, RefundRequestOut.from_orm)
    return 200, result


@router.get(
    "/my-refund-requests",
    response={200: PageOut[RefundRequestOut], 404: MessageOut},
    auth=ClientOnlyAuth(),
    summary="Cliente lista o histórico dos próprios pedidos de reembolso",
)
@ratelimit(key="user", rate="30/m", block=True)
def list_my_refund_requests_router(request, page: int = 1, page_size: int = PAGE_SIZE_DEFAULT):
    client = get_client_by_user_id(user_id=request.auth.id)
    if client is None:
        return 404, {"detail": "Cliente não encontrado."}

    qs = get_refund_requests_for_client(client.id)
    result = paginate_queryset(qs, page, page_size, RefundRequestOut.from_orm)
    return 200, result


@router.get(
    "/{refund_request_id}",
    response={200: RefundRequestOut, 404: MessageOut},
    auth=AdminOnlyAuth(),
    summary="Admin vê o detalhe de um pedido de reembolso",
)
@ratelimit(key="user", rate="30/m", block=True)
def get_refund_request_router(request, refund_request_id: UUID):
    refund_request = get_refund_request_by_id(refund_request_id)
    if refund_request is None:
        return 404, {"detail": "Pedido de reembolso não encontrado."}
    return 200, RefundRequestOut.from_orm(refund_request)


@router.post(
    "/{refund_request_id}/approve",
    response={200: RefundRequestOut, 400: MessageOut, 404: MessageOut},
    auth=AdminOnlyAuth(),
    summary="Admin aprova o pedido — aciona o estorno de verdade na Asaas",
)
@ratelimit(key="user", rate="20/m", block=True)
def approve_refund_request_router(request, refund_request_id: UUID, payload: RefundRequestReviewIn):
    try:
        refund_request = approve_refund_request_service(
            refund_request_id=refund_request_id,
            reviewed_by=request.auth,
            admin_notes=payload.admin_notes,
        )
        return 200, RefundRequestOut.from_orm(refund_request)
    except RefundRequestNotFound as e:
        return 404, {"detail": str(e)}
    except RefundRequestAlreadyReviewed as e:
        return 400, {"detail": str(e)}
    except PaymentNotRefundable as e:
        return 400, {"detail": str(e)}
    except AsaasAPIError as e:
        return 400, {"detail": f"Falha ao estornar na Asaas: {e.message}"}


@router.post(
    "/{refund_request_id}/reject",
    response={200: RefundRequestOut, 400: MessageOut, 404: MessageOut},
    auth=AdminOnlyAuth(),
    summary="Admin rejeita o pedido — nenhum dinheiro é movimentado",
)
@ratelimit(key="user", rate="20/m", block=True)
def reject_refund_request_router(request, refund_request_id: UUID, payload: RefundRequestReviewIn):
    try:
        refund_request = reject_refund_request_service(
            refund_request_id=refund_request_id,
            reviewed_by=request.auth,
            admin_notes=payload.admin_notes,
        )
        return 200, RefundRequestOut.from_orm(refund_request)
    except RefundRequestNotFound as e:
        return 404, {"detail": str(e)}
    except RefundRequestAlreadyReviewed as e:
        return 400, {"detail": str(e)}