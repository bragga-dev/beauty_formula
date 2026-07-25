"""
Queries de EmployeeService — vínculos entre funcionários e os serviços
que eles estão aptos a atender.
"""
from typing import List, Optional
from uuid import UUID

from django.db.models import Q, QuerySet

from beauty_formula.apps.services.models.employee_service import EmployeeService


# ═══════════════════════════════════════════════════════════════════════════════
# Buscas Básicas por ID
# ═══════════════════════════════════════════════════════════════════════════════

def get_employee_service_by_id(employee_service_id: UUID) -> Optional[EmployeeService]:
    """Retorna o vínculo pelo ID, ou None se não existir."""
    return (
        EmployeeService.objects
        .select_related("employee", "service")
        .filter(id=employee_service_id)
        .first()
    )


def get_employee_service(employee_id: UUID, service_id: UUID) -> Optional[EmployeeService]:
    """
    Retorna o vínculo entre um funcionário e um serviço específico,
    ativo ou não — usado antes de criar, pra saber se é create ou reativação.
    """
    return EmployeeService.objects.filter(employee_id=employee_id, service_id=service_id).first()


# ═══════════════════════════════════════════════════════════════════════════════
# Listagem por Funcionário
# ═══════════════════════════════════════════════════════════════════════════════

def get_services_for_employee(employee_id: UUID, active_only: bool = True) -> QuerySet[EmployeeService]:
    """Retorna os vínculos de serviço de um funcionário específico."""
    qs = EmployeeService.objects.select_related("service").filter(employee_id=employee_id)
    if active_only:
        qs = qs.filter(is_active=True)
    return qs.order_by("service__name")


# ═══════════════════════════════════════════════════════════════════════════════
# Listagem por Serviço
# ═══════════════════════════════════════════════════════════════════════════════

def get_employees_for_service(service_id: UUID, active_only: bool = True) -> QuerySet[EmployeeService]:
    """Retorna os funcionários vinculados a um serviço específico."""
    qs = EmployeeService.objects.select_related("employee").filter(service_id=service_id)
    if active_only:
        qs = qs.filter(is_active=True)
    return qs.order_by("employee__first_name")


# ═══════════════════════════════════════════════════════════════════════════════
# Utilitários
# ═══════════════════════════════════════════════════════════════════════════════

def validate_employee_service_exists(employee_id: UUID, service_id: UUID) -> bool:
    """Verifica se já existe vínculo (ativo ou não) entre funcionário e serviço."""
    return EmployeeService.objects.filter(employee_id=employee_id, service_id=service_id).exists()


# ═══════════════════════════════════════════════════════════════════════════════
# Busca
# ═══════════════════════════════════════════════════════════════════════════════

def search_employee_service(query: str, search_fields: List[str] = None) -> QuerySet[EmployeeService]:
    """
    Busca vínculos EmployeeService por campos do funcionário e do serviço vinculados.

    Args:
        query: Termo de busca
        search_fields: Campos para buscar (default: username, first_name, last_name, bio do
            funcionário + name, description do serviço). Não inclui price/duration —
            icontains não faz sentido em campo numérico/duration.
    Returns:
        QuerySet[EmployeeService]: Vínculos ativos cujo funcionário ou serviço casa com o termo
    """
    if not query:
        return EmployeeService.objects.none()

    if search_fields is None:
        search_fields = [
            'employee__username',
            'employee__first_name',
            'employee__last_name',
            'employee__bio',
            'service__name',
            'service__description',
        ]

    q_objects = Q()
    for field in search_fields:
        q_objects |= Q(**{f"{field}__icontains": query})

    return (
        EmployeeService.objects
        .filter(q_objects, is_active=True)
        .select_related('employee', 'service')
        .order_by('employee__first_name', 'employee__last_name')
    )