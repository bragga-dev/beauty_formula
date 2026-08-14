"""
Repository de EmployeeService — funções de persistência (criação,
ativação/desativação e exclusão) do vínculo entre funcionário e serviço.

Como no repository de Service, essas funções recebem valores já resolvidos
(instâncias de model, não IDs) — resolver `employee_id`/`service_id` pra
instância é responsabilidade da camada de `services.py`, não daqui.
"""
from django.db import transaction

from beauty_formula.apps.accounts.models.employee import Employee
from beauty_formula.apps.services.models.employee_service import EmployeeService
from beauty_formula.apps.services.models.service import Service


@transaction.atomic
def create_employee_service(*, employee: Employee, service: Service) -> EmployeeService:
    """
    Cria o vínculo entre um funcionário e um serviço. Roda full_clean()
    antes de salvar (via EmployeeService.save()) — a UniqueConstraint
    garante que não dá pra duplicar o mesmo par (employee, service).
    """
    employee_service = EmployeeService(employee=employee, service=service)
    employee_service.save()
    return employee_service


@transaction.atomic
def activate_employee_service(employee_service: EmployeeService) -> EmployeeService:
    """Reativa um vínculo desativado."""
    employee_service.is_active = True
    employee_service.save(update_fields=["is_active"])
    return employee_service


@transaction.atomic
def deactivate_employee_service(employee_service: EmployeeService) -> EmployeeService:
    """
    Desativa um vínculo (soft delete). Preferível a apagar de verdade —
    mantém histórico de agendamentos que foram feitos enquanto o
    funcionário atendia esse serviço.
    """
    employee_service.is_active = False
    employee_service.save(update_fields=["is_active"])
    return employee_service


@transaction.atomic
def delete_employee_service(employee_service: EmployeeService) -> None:
    """
    Exclui o vínculo permanentemente do banco.
    Use com cautela — prefira `deactivate_employee_service` na maioria
    dos casos, já que `on_delete=PROTECT` em `employee`/`service` só
    protege contra apagar o Employee/Service em si, não este vínculo.
    """
    employee_service.delete()