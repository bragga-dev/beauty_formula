"""
Queries de EmployeeCommission — leitura pro CRUD/listagem administrativa,
pra visão do próprio funcionário, e pra geração/conferência em lote por
período (quantos atendimentos concluídos existem no período x quantos já
têm comissão gerada).
"""
from datetime import date
from typing import Optional
import uuid

from django.db.models import Q, QuerySet, Sum

from beauty_formula.apps.payment.models.employee_commission_model import EmployeeCommission
from beauty_formula.apps.services.models.scheduling import Scheduling

DEFAULT_RELATED = (
    "employee",
    "employee__user",
    "scheduling",
    "scheduling__service",
    "scheduling__client",
    "scheduling__client__user",
)


# ═══════════════════════════════════════════════════════════════════════════════
# Buscas Básicas por ID
# ═══════════════════════════════════════════════════════════════════════════════

def get_commission_by_id(commission_id: uuid.UUID) -> Optional[EmployeeCommission]:
    """Retorna uma comissão pelo ID."""
    return EmployeeCommission.objects.select_related(*DEFAULT_RELATED).filter(id=commission_id).first()


def get_commission_by_scheduling(scheduling_id: uuid.UUID) -> Optional[EmployeeCommission]:
    """Retorna a comissão vinculada a um agendamento (relação é OneToOne)."""
    return EmployeeCommission.objects.select_related(*DEFAULT_RELATED).filter(scheduling_id=scheduling_id).first()


def get_commissions_by_ids(
    commission_ids: list[uuid.UUID],
    status: Optional[str] = None,
) -> QuerySet[EmployeeCommission]:
    """
    Retorna as comissões existentes cujo ID esteja na lista informada —
    base da marcação em lote por seleção manual (`update_status_bulk`).
    `status` opcional restringe a busca (ex.: só as ainda PENDING, pra
    ignorar silenciosamente quem já foi paga/cancelada e for reenviada
    por engano numa seleção antiga).
    """
    qs = EmployeeCommission.objects.select_related(*DEFAULT_RELATED).filter(id__in=commission_ids)
    if status:
        qs = qs.filter(status=status)
    return qs


# ═══════════════════════════════════════════════════════════════════════════════
# Listagem administrativa com filtros
# ═══════════════════════════════════════════════════════════════════════════════

def filter_commissions(
    employee_id: Optional[uuid.UUID] = None,
    status: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    competencia: Optional[date] = None,
) -> QuerySet[EmployeeCommission]:
    """
    Listagem administrativa de comissões com filtros combináveis.

    `start_date`/`end_date` continuam filtrando pela data do ATENDIMENTO
    (scheduling__scheduled_time) — úteis pra períodos ad-hoc (ex.: "toda
    quinzena"). `competencia`, se informado, filtra pelo mês de
    referência da comissão (qualquer dia do mês desejado serve; o filtro
    normaliza pro mês inteiro) — é o filtro certo pra relatório mensal
    auditável, já que reflete o valor que pode ter sido corrigido
    manualmente pelo admin, e não necessariamente a data real do
    agendamento.
    """
    q = Q()

    if employee_id:
        q &= Q(employee_id=employee_id)
    if status:
        q &= Q(status=status)
    if start_date:
        q &= Q(scheduling__scheduled_time__date__gte=start_date)
    if end_date:
        q &= Q(scheduling__scheduled_time__date__lte=end_date)
    if competencia:
        q &= Q(competencia__year=competencia.year, competencia__month=competencia.month)

    return EmployeeCommission.objects.select_related(*DEFAULT_RELATED).filter(q).order_by("-scheduling__scheduled_time")


# ═══════════════════════════════════════════════════════════════════════════════
# Buscas por Funcionário
# ═══════════════════════════════════════════════════════════════════════════════

def get_commissions_by_employee(
    employee_id: uuid.UUID,
    status: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
) -> QuerySet[EmployeeCommission]:
    """Comissões de um funcionário específico, com os mesmos filtros de período/status."""
    return filter_commissions(employee_id=employee_id, status=status, start_date=start_date, end_date=end_date)


# ═══════════════════════════════════════════════════════════════════════════════
# Geração / conferência em lote por período
# ═══════════════════════════════════════════════════════════════════════════════

def count_completed_schedulings_in_period(
    employee_id: Optional[uuid.UUID],
    start_date: date,
    end_date: date,
) -> int:
    """
    Total de atendimentos CONCLUÍDOS no período (com ou sem comissão já
    gerada). `employee_id=None` conta de todos os funcionários.
    """
    qs = Scheduling.objects.filter(
        status=Scheduling.SchedulingStatus.COMPLETED,
        scheduled_time__date__range=(start_date, end_date),
    )
    if employee_id:
        qs = qs.filter(employee_id=employee_id)
    return qs.count()


def list_completed_schedulings_without_commission(
    employee_id: Optional[uuid.UUID] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
) -> QuerySet[Scheduling]:
    """
    Agendamentos COMPLETED que ainda não têm EmployeeCommission gerada —
    a base da geração em lote. Rodar a geração de novo pro mesmo período
    não duplica nada: quem já tem comissão simplesmente não aparece mais
    aqui.
    """
    q = Q(status=Scheduling.SchedulingStatus.COMPLETED, commission__isnull=True)

    if employee_id:
        q &= Q(employee_id=employee_id)
    if start_date:
        q &= Q(scheduled_time__date__gte=start_date)
    if end_date:
        q &= Q(scheduled_time__date__lte=end_date)

    return Scheduling.objects.select_related("service", "employee", "client").filter(q).order_by("scheduled_time")


def get_commission_totals(
    employee_id: Optional[uuid.UUID] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    competencia: Optional[date] = None,
) -> dict:
    """
    Soma o valor das comissões por status, dentro dos mesmos filtros de
    funcionário/período/competência usados na listagem — independe de um
    filtro de status pontual, pra sempre mostrar o quadro completo
    (quanto falta pagar, quanto já foi pago, quanto foi cancelado).
    """
    qs = filter_commissions(employee_id=employee_id, status=None, start_date=start_date, end_date=end_date, competencia=competencia)

    aggregated = qs.aggregate(
        total_pending=Sum("commission_value", filter=Q(status=EmployeeCommission.CommissionStatus.PENDING)),
        total_paid=Sum("commission_value", filter=Q(status=EmployeeCommission.CommissionStatus.PAID)),
        total_canceled=Sum("commission_value", filter=Q(status=EmployeeCommission.CommissionStatus.CANCELED)),
    )

    return {
        "total_pending": aggregated["total_pending"] or 0,
        "total_paid": aggregated["total_paid"] or 0,
        "total_canceled": aggregated["total_canceled"] or 0,
        "pending_count": qs.filter(status=EmployeeCommission.CommissionStatus.PENDING).count(),
        "paid_count": qs.filter(status=EmployeeCommission.CommissionStatus.PAID).count(),
        "canceled_count": qs.filter(status=EmployeeCommission.CommissionStatus.CANCELED).count(),
    }


def get_pending_commissions_in_period(
    employee_id: Optional[uuid.UUID],
    start_date: date,
    end_date: date,
) -> QuerySet[EmployeeCommission]:
    """Instâncias das comissões PENDING de um período — alvo da atualização de status em lote."""
    return filter_commissions(
        employee_id=employee_id,
        status=EmployeeCommission.CommissionStatus.PENDING,
        start_date=start_date,
        end_date=end_date,
    )


def list_distinct_competencias(employee_id: Optional[uuid.UUID] = None) -> list[date]:
    """
    Meses de competência distintos que de fato têm alguma comissão —
    base pro dropdown de filtro "dinâmico" no front (só mostra
    ano/mês que existem de verdade, em vez de um intervalo fixo
    arbitrário). Mais recente primeiro.
    """
    qs = EmployeeCommission.objects.all()
    if employee_id:
        qs = qs.filter(employee_id=employee_id)
    return list(qs.order_by("-competencia").values_list("competencia", flat=True).distinct())