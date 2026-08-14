"""
Queries de EmployeeWorkingHours — janelas de horário de trabalho por
dia da semana.
"""
from typing import Optional
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


def get_all_working_hours_for_employee(employee_id: UUID) -> QuerySet[EmployeeWorkingHours]:
    """Retorna a semana inteira de turnos cadastrados de um funcionário."""
    return (
        EmployeeWorkingHours.objects
        .filter(employee_id=employee_id)
        .order_by("weekday", "start_time")
    )


def get_working_hours_by_id(working_hours_id: UUID) -> Optional[EmployeeWorkingHours]:
    """Busca um turno pelo ID. Retorna None se não existir."""
    return EmployeeWorkingHours.objects.filter(pk=working_hours_id).first()