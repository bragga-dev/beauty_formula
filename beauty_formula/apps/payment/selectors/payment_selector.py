"""
Queries de Payment — leitura pro CRUD/listagem administrativa e pro
webhook (achar o Payment local a partir do id da Asaas).
"""
from datetime import date
from typing import Optional
import uuid

from django.db.models import Q, QuerySet

from beauty_formula.apps.payment.models.payment_model import Payment

DEFAULT_RELATED = ("scheduling", "client", "client__user")


# ═══════════════════════════════════════════════════════════════════════════════
# Buscas Básicas por ID
# ═══════════════════════════════════════════════════════════════════════════════

def get_payment_by_id(payment_id: uuid.UUID) -> Optional[Payment]:
    """Retorna um pagamento pelo ID interno."""
    return Payment.objects.select_related(*DEFAULT_RELATED).filter(id=payment_id).first()


def get_payment_by_asaas_id(asaas_payment_id: str) -> Optional[Payment]:
    """Retorna um pagamento pelo id da cobrança na Asaas — usado pelo endpoint de webhook."""
    return Payment.objects.select_related(*DEFAULT_RELATED).filter(asaas_payment_id=asaas_payment_id).first()


# ═══════════════════════════════════════════════════════════════════════════════
# Buscas por Agendamento / Cliente
# ═══════════════════════════════════════════════════════════════════════════════

def get_payments_by_scheduling(scheduling_id: uuid.UUID) -> Payment:
    """Retorna um Pagamento associado a determinado Agendamento."""
    return Payment.objects.select_related(*DEFAULT_RELATED).get(scheduling_id=scheduling_id)


def get_active_payment_for_scheduling(scheduling_id: uuid.UUID) -> Optional[Payment]:
    """A cobrança 'vigente' de um agendamento — pendente ou já paga. None se nunca foi cobrado ou só há cobranças mortas (cancelada/vencida/falhou)."""
    active_statuses = [Payment.PaymentStatus.PENDING, Payment.PaymentStatus.RECEIVED, Payment.PaymentStatus.CONFIRMED]
    return (
        Payment.objects.select_related(*DEFAULT_RELATED)
        .filter(scheduling_id=scheduling_id, status__in=active_statuses)
        .order_by("-created_at")
        .first()
    )


def get_payments_by_client(client_id: uuid.UUID) -> QuerySet[Payment]:
    """Todas as cobranças de um cliente."""
    return Payment.objects.select_related(*DEFAULT_RELATED).filter(client_id=client_id).order_by("-created_at")


# ═══════════════════════════════════════════════════════════════════════════════
# Listagem administrativa com filtros
# ═══════════════════════════════════════════════════════════════════════════════

def filter_payments(
    client_id: Optional[uuid.UUID] = None,
    status: Optional[str] = None,
    billing_type: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    synced: Optional[bool] = None,
) -> QuerySet[Payment]:
    """Listagem administrativa de pagamentos com filtros combináveis. Nenhum filtro informado retorna tudo."""
    q = Q()

    if client_id:
        q &= Q(client_id=client_id)
    if status:
        q &= Q(status=status)
    if billing_type:
        q &= Q(billing_type=billing_type)
    if start_date:
        q &= Q(due_date__gte=start_date)
    if end_date:
        q &= Q(due_date__lte=end_date)
    if synced is not None:
        q &= Q(synced_with_asaas=synced)

    return Payment.objects.select_related(*DEFAULT_RELATED).filter(q).order_by("-created_at")