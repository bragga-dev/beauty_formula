"""
Queries de EmployeeCommission — leitura pro CRUD/listagem administrativa,
pra visão do próprio funcionário, e pra geração/conferência em lote por
período (quantos atendimentos concluídos existem no período x quantos já
têm comissão gerada).
"""
from datetime import date
from typing import Optional
import uuid

from django.db.models import Q, QuerySet

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


# ═══════════════════════════════════════════════════════════════════════════════
# Listagem administrativa com filtros
# ═══════════════════════════════════════════════════════════════════════════════

def filter_commissions(
    employee_id: Optional[uuid.UUID] = None,
    status: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
) -> QuerySet[EmployeeCommission]:
    """
    Listagem administrativa de comissões com filtros combináveis.
    O período filtra pela data do ATENDIMENTO (scheduling__scheduled_time),
    não pela data de criação do registro de comissão.
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