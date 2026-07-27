"""
Queries de EmployeeTimeOff — bloqueios de horário (recorrentes ou
pontuais) de um funcionário.
"""
from datetime import date as date_type
from uuid import UUID

from django.db.models import Q, QuerySet

from beauty_formula.apps.services.models.employee_time_off import EmployeeTimeOff


def get_time_off_for_employee_on_date(employee_id: UUID, weekday: int, target_date: date_type) -> QuerySet[EmployeeTimeOff]:
    """
    Retorna os bloqueios de um funcionário que afetam uma data específica:
    - Recorrentes cujo `weekday` bate com o dia da semana da data.
    - Pontuais cujo intervalo [start_datetime, end_datetime] toca em
      algum momento daquela data (comparação por dia, não por instante
      exato — um bloqueio que começa 23h de um dia e vai até 2h do
      seguinte deve aparecer nos dois dias).
    """
    return EmployeeTimeOff.objects.filter(employee_id=employee_id).filter(Q(weekday=weekday) | Q(start_datetime__date__lte=target_date, 
        end_datetime__date__gte=target_date)
    )