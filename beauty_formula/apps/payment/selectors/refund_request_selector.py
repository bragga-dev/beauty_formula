"""
Queries de RefundRequest — leitura pra fila de análise do admin e pra
"meus pedidos de reembolso" do cliente.
"""
import uuid
from typing import Optional

from django.db.models import Q, QuerySet

from beauty_formula.apps.payment.models.refund_request_model import RefundRequest

DEFAULT_RELATED = (
    "payment",
    "payment__scheduling",
    "payment__scheduling__service",
    "client",
    "client__user",
    "requested_by",
    "reviewed_by",
)


def get_refund_request_by_id(refund_request_id: uuid.UUID) -> Optional[RefundRequest]:
    return RefundRequest.objects.select_related(*DEFAULT_RELATED).filter(id=refund_request_id).first()


def get_pending_refund_request_for_payment(payment_id: uuid.UUID) -> Optional[RefundRequest]:
    """
    Usado antes de criar um novo pedido — a `UniqueConstraint` condicional
    do model já impede duplicidade no banco, mas checar aqui primeiro
    permite devolver uma mensagem de domínio clara (`RefundRequestAlreadyExists`)
    em vez de deixar o IntegrityError estourar cru até o repository.
    """
    return RefundRequest.objects.filter(payment_id=payment_id, status=RefundRequest.RefundRequestStatus.PENDING).first()


def filter_refund_requests(*, status: Optional[str] = None) -> QuerySet[RefundRequest]:
    """Fila de análise do admin — filtro opcional por status (default: mostra todos, mais recentes primeiro)."""
    qs = RefundRequest.objects.select_related(*DEFAULT_RELATED).all()
    if status:
        qs = qs.filter(status=status)
    return qs


def get_refund_requests_for_client(client_id: uuid.UUID) -> QuerySet[RefundRequest]:
    """"Meus pedidos de reembolso" — histórico do próprio cliente."""
    return RefundRequest.objects.select_related(*DEFAULT_RELATED).filter(client_id=client_id)