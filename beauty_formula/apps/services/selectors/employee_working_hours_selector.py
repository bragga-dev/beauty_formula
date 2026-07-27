"""
Queries de EmployeeWorkingHours — janelas de horário de trabalho por
dia da semana.
"""
from uuid import UUID

from django.db.models import QuerySet

from beauty_formula.apps.services.models.employee_works_hours import EmployeeWorkingHours


def get_working_hours_for_employee_weekday(employee_id: UUID, weekday: int) -> QuerySet[EmployeeWorkingHours]:
    """Retorna os turnos cadastrados de um funcionário pra um dia da semana específico."""
    return (
        EmployeeWorkingHours.objects
        .filter(employee_id=employee_id, weekday=weekday)
        .order_by("start_time")
    )