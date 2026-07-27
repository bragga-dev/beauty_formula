"""
Queries de EmployeeTimeOff — bloqueios de horário (recorrentes ou
pontuais) de um funcionário.
"""
from datetime import date as date_type, datetime, timedelta
from typing import Optional, List
from uuid import UUID
from django.utils import timezone
from django.db.models import Q, QuerySet

from beauty_formula.apps.services.models.employee_time_off import EmployeeTimeOff


# ═══════════════════════════════════════════════════════════════════════════════
# Buscas Básicas por ID
# ═══════════════════════════════════════════════════════════════════════════════

def get_time_off_by_id(time_off_id: UUID) -> Optional[EmployeeTimeOff]:
    """Retorna um bloqueio pelo ID, ou None se não existir."""
    return EmployeeTimeOff.objects.filter(id=time_off_id).first()


# ═══════════════════════════════════════════════════════════════════════════════
# Listagem por Funcionário
# ═══════════════════════════════════════════════════════════════════════════════

def get_time_off_for_employee(employee_id: UUID) -> QuerySet[EmployeeTimeOff]:
    """Retorna todos os bloqueios de um funcionário."""
    return EmployeeTimeOff.objects.filter(employee_id=employee_id).order_by("-start_datetime", "weekday")


def get_recurring_time_off_for_employee(employee_id: UUID) -> QuerySet[EmployeeTimeOff]:
    """Retorna apenas bloqueios recorrentes de um funcionário."""
    return EmployeeTimeOff.objects.filter(employee_id=employee_id, weekday__isnull=False).order_by("weekday", "start_time")


def get_punctual_time_off_for_employee(employee_id: UUID) -> QuerySet[EmployeeTimeOff]:
    """Retorna apenas bloqueios pontuais de um funcionário."""
    return EmployeeTimeOff.objects.filter(employee_id=employee_id, start_datetime__isnull=False).order_by("-start_datetime")


def get_time_off_by_block_type(employee_id: UUID, block_type: str) -> QuerySet[EmployeeTimeOff]:
    """Retorna bloqueios de um funcionário por tipo."""
    return EmployeeTimeOff.objects.filter(employee_id=employee_id, block_type=block_type).order_by("-start_datetime", "weekday")


# ═══════════════════════════════════════════════════════════════════════════════
# Buscas por Data
# ═══════════════════════════════════════════════════════════════════════════════

def get_time_off_for_employee_on_date(employee_id: UUID, weekday: int, target_date: date_type) -> QuerySet[EmployeeTimeOff]:
    """
    Retorna os bloqueios de um funcionário que afetam uma data específica:
    - Recorrentes cujo `weekday` bate com o dia da semana da data.
    - Pontuais cujo intervalo [start_datetime, end_datetime] toca em
      algum momento daquela data (comparação por dia, não por instante
      exato — um bloqueio que começa 23h de um dia e vai até 2h do
      seguinte deve aparecer nos dois dias).
    """
    return EmployeeTimeOff.objects.filter(
        employee_id=employee_id
    ).filter(
        Q(weekday=weekday) | 
        Q(
            start_datetime__date__lte=target_date,
            end_datetime__date__gte=target_date
        )
    )


def get_time_off_for_employee_date_range(employee_id: UUID, start_date: date_type, end_date: date_type) -> QuerySet[EmployeeTimeOff]:
    """
    Retorna bloqueios de um funcionário em um período.
    """
    return EmployeeTimeOff.objects.filter(employee_id=employee_id
    ).filter(
        # Bloqueios recorrentes (qualquer dia da semana no período)
        Q(weekday__isnull=False) |
        # Bloqueios pontuais que intersectam o período
        Q(
            start_datetime__date__lte=end_date,
            end_datetime__date__gte=start_date
        )
    ).distinct()


def get_active_time_off_for_employee(employee_id: UUID) -> QuerySet[EmployeeTimeOff]:
    """
    Retorna bloqueios ativos de um funcionário (considerando data/hora atual).
    """
    now = timezone.now()
    local_now = timezone.localtime(now)
    today_weekday = local_now.weekday()
    current_time = local_now.time()
    
    return EmployeeTimeOff.objects.filter(
        employee_id=employee_id
    ).filter(
        # Bloqueios recorrentes (por dia da semana)
        Q(
            weekday=today_weekday,
            start_time__lte=current_time,
            end_time__gte=current_time
        ) |
        # Bloqueios pontuais (por data/hora)
        Q(
            start_datetime__lte=now,
            end_datetime__gte=now
        )
    )


def get_upcoming_time_off_for_employee(employee_id: UUID, days_ahead: int = 7) -> QuerySet[EmployeeTimeOff]:
    """
    Retorna bloqueios futuros (próximos N dias).
    """
    
    
    now = timezone.now()
    future_date = now + timezone.timedelta(days=days_ahead)
    
    return EmployeeTimeOff.objects.filter(
        employee_id=employee_id
    ).filter(
        Q(
            start_datetime__gte=now,
            start_datetime__lte=future_date
        ) |
        Q(
            weekday__in=[
                (now + timezone.timedelta(days=i)).weekday()
                for i in range(days_ahead + 1)
            ]
        )
    ).distinct()


# ═══════════════════════════════════════════════════════════════════════════════
# Validação/Conflitos
# ═══════════════════════════════════════════════════════════════════════════════

def get_time_off_conflicts(
    employee_id: UUID,
    start_datetime: datetime,
    end_datetime: datetime
) -> QuerySet[EmployeeTimeOff]:
    """
    Verifica conflitos de bloqueio para um período específico.
    Retorna bloqueios que se sobrepõem ao período informado.
    """
    start_date = start_datetime.date()
    end_date = end_datetime.date()
    
    return EmployeeTimeOff.objects.filter(
        employee_id=employee_id
    ).filter(
        # Bloqueios pontuais que se sobrepõem
        Q(
            start_datetime__lt=end_datetime,
            end_datetime__gt=start_datetime
        ) |
        # Bloqueios recorrentes que caem nos dias do período
        Q(
            weekday__in=[
                (start_date + timedelta(days=i)).weekday()
                for i in range((end_date - start_date).days + 1)
            ],
            start_time__lt=end_datetime.time(),
            end_time__gt=start_datetime.time()
        )
    )


def has_time_off_conflict(
    employee_id: UUID,
    start_datetime: datetime,
    end_datetime: datetime
) -> bool:
    """Verifica se existe conflito de bloqueio para um período."""
    return get_time_off_conflicts(employee_id, start_datetime, end_datetime).exists()


# ═══════════════════════════════════════════════════════════════════════════════
# Utilitários
# ═══════════════════════════════════════════════════════════════════════════════

def validate_time_off_exists(time_off_id: UUID) -> bool:
    """Verifica se um bloqueio existe."""
    return EmployeeTimeOff.objects.filter(id=time_off_id).exists()


def validate_time_off_belongs_to_employee(time_off_id: UUID, employee_id: UUID) -> bool:
    """Verifica se um bloqueio pertence a um funcionário específico."""
    return EmployeeTimeOff.objects.filter(id=time_off_id, employee_id=employee_id).exists()