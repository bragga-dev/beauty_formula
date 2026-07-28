"""
Queries de Scheduling — usado pelo CRUD de agendamentos e pelo cálculo de
disponibilidade, pra saber quais horários do funcionário já estão ocupados.
"""
from datetime import date as date_type, datetime, timedelta
from typing import Optional
import uuid

from django.db.models import Q, QuerySet

from beauty_formula.apps.services.models.scheduling import Scheduling

# Status que efetivamente ocupam a agenda do funcionário. Concluído/
# cancelado/no-show não bloqueiam novos horários.
BUSY_STATUSES = [
    Scheduling.SchedulingStatus.PENDING,
    Scheduling.SchedulingStatus.CONFIRMED,
    Scheduling.SchedulingStatus.IN_PROGRESS,
]

# select_related padrão pra qualquer listagem/detalhe que vá virar
# SchedulingOut/SchedulingPrivateOut — evita N+1 ao montar client/employee/
# service/canceled_by aninhados.
DEFAULT_RELATED = ("service", "client", "client__user", "employee", "employee__user", "canceled_by")


# ═══════════════════════════════════════════════════════════════════════════════
# Buscas Básicas por ID
# ═══════════════════════════════════════════════════════════════════════════════

def get_scheduling_by_id(scheduling_id: uuid.UUID) -> Optional[Scheduling]:
    """Retorna um agendamento pelo ID, independente do status."""
    return Scheduling.objects.select_related(*DEFAULT_RELATED).filter(id=scheduling_id).first()


def get_scheduling_by_id_active(scheduling_id: uuid.UUID) -> Optional[Scheduling]:
    """Retorna um agendamento pelo ID que esteja ATIVO."""
    return Scheduling.objects.select_related(*DEFAULT_RELATED).filter(id=scheduling_id, is_active=True).first()


def get_scheduling_by_id_inactive(scheduling_id: uuid.UUID) -> Optional[Scheduling]:
    """Retorna um agendamento pelo ID que esteja INATIVO."""
    return Scheduling.objects.select_related(*DEFAULT_RELATED).filter(id=scheduling_id, is_active=False).first()


# ═══════════════════════════════════════════════════════════════════════════════
# Buscas por Funcionário
# ═══════════════════════════════════════════════════════════════════════════════

def get_schedulings_by_employee(employee_id: uuid.UUID, active_only: bool = False) -> QuerySet[Scheduling]:
    """Retorna os agendamentos que um funcionário tem."""
    qs = Scheduling.objects.select_related(*DEFAULT_RELATED).filter(employee_id=employee_id)
    if active_only:
        qs = qs.filter(is_active=True)
    return qs.order_by("-scheduled_time")


# ═══════════════════════════════════════════════════════════════════════════════
# Buscas por Cliente
# ═══════════════════════════════════════════════════════════════════════════════

def get_schedulings_by_client(client_id: uuid.UUID, active_only: bool = False) -> QuerySet[Scheduling]:
    """Retorna todos os agendamentos que um cliente tem."""
    qs = Scheduling.objects.select_related(*DEFAULT_RELATED).filter(client_id=client_id)
    if active_only:
        qs = qs.filter(is_active=True)
    return qs.order_by("-scheduled_time")


# ═══════════════════════════════════════════════════════════════════════════════
# Buscas por Cliente e Funcionário
# ═══════════════════════════════════════════════════════════════════════════════

def get_schedulings_by_client_and_employee(client_id: uuid.UUID, employee_id: uuid.UUID) -> QuerySet[Scheduling]:
    """Retorna todos os agendamentos que um cliente e um funcionário têm em comum."""
    return (
        Scheduling.objects.select_related(*DEFAULT_RELATED)
        .filter(client_id=client_id, employee_id=employee_id)
        .order_by("-scheduled_time")
    )


# ═══════════════════════════════════════════════════════════════════════════════
# Listagem administrativa com filtros
# ═══════════════════════════════════════════════════════════════════════════════

def filter_schedulings(
    service_id: Optional[uuid.UUID] = None,
    employee_id: Optional[uuid.UUID] = None,
    client_id: Optional[uuid.UUID] = None,
    status: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    is_active: Optional[bool] = None,
) -> QuerySet[Scheduling]:
    """
    Listagem administrativa de agendamentos com filtros combináveis.
    Nenhum filtro informado retorna tudo.
    """
    q = Q()

    if service_id:
        q &= Q(service_id=service_id)
    if employee_id:
        q &= Q(employee_id=employee_id)
    if client_id:
        q &= Q(client_id=client_id)
    if status:
        q &= Q(status=status)
    if start_date:
        q &= Q(scheduled_time__gte=start_date)
    if end_date:
        q &= Q(scheduled_time__lte=end_date)
    if is_active is not None:
        q &= Q(is_active=is_active)

    return Scheduling.objects.select_related(*DEFAULT_RELATED).filter(q).order_by("-scheduled_time")


# ═══════════════════════════════════════════════════════════════════════════════
# Disponibilidade — ocupação da agenda do funcionário
# ═══════════════════════════════════════════════════════════════════════════════

def get_active_schedulings_for_employee_on_date(employee_id: uuid.UUID, target_date: date_type) -> QuerySet[Scheduling]:
    """
    Retorna os agendamentos que podem ocupar a agenda do funcionário numa
    data específica.

    A janela de busca é levemente mais ampla que o próprio dia (pega
    também o dia anterior) pra não perder um agendamento que começou
    tarde da noite e termina depois da meia-noite. A subtração de
    intervalos feita depois (availability_selector) descarta qualquer
    coisa que não se sobreponha de verdade à data pedida.
    """
    return Scheduling.objects.filter(
        employee_id=employee_id,
        is_active=True,
        status__in=BUSY_STATUSES,
        scheduled_time__date__in=[target_date - timedelta(days=1), target_date],
    )