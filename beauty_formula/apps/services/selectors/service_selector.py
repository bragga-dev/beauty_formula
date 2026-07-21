"""
Queries de Serviço — Funções para buscar serviços.
"""
from typing import Optional
from uuid import UUID
from django.db.models import QuerySet

from beauty_formula.apps.services.models.service import Service


def get_service_by_id(service_id: UUID) -> Optional[Service]:
    """Retorna o serviço pelo ID, ou None se não existir."""
    try:
        return Service.objects.get(id=service_id)
    except Service.DoesNotExist:
        return None


def get_services_for_employee(employee_id: UUID) -> QuerySet[Service]:
    """
    Retorna os serviços que um funcionário está apto a atender
    (via EmployeeService.active=True).
    """
    return Service.objects.filter(
        employee_assignments__employee_id=employee_id,
        employee_assignments__active=True,
    ).distinct().order_by("name")


__all__ = [
    "get_service_by_id",
    "get_services_for_employee",
]