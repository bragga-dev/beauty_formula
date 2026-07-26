import uuid

from beauty_formula.apps.services.schemas.employee_service_schema import (
    EmployeeServiceCreateIn,
    EmployeeServiceOut,
    EmployeeServicePrivateOut,
    EmployeeServiceUpdateIn,
)

from beauty_formula.apps.accounts.selectors.employee_selector import (
    get_employee_by_id,
    get_employee_by_user_id,
)

from beauty_formula.apps.services.selectors.service_selector import (
    get_service_by_id,
)
from beauty_formula.apps.services.selectors.employee_service_selector import (
    get_employee_service,
    get_employee_service_by_id,
    get_employees_for_service,
    get_services_for_employee,
)
from beauty_formula.apps.core.exceptions.permissions import EmployeeNotFoundError
from beauty_formula.apps.core.exceptions.service_exception import (
    ServiceNotFound,
    AssociationAlreadyExists,
    AssociationNotFound,
)
from beauty_formula.apps.services.repositories.employee_service_repository import (
    create_employee_service,
    deactivate_employee_service,
    delete_employee_service,
    activate_employee_service,
)
from beauty_formula.apps.accounts.selectors.user_selector import (
    get_user_with_related,

)

def create_employee_service_for_employee(user_id: uuid.UUID, data: EmployeeServiceCreateIn) -> EmployeeServicePrivateOut:
    """
    Funcionário vincula um serviço que passa a atender.

    Se já existe um vínculo *desativado* com esse serviço, reativa em vez
    de criar duplicado — a UniqueConstraint no model bloquearia a
    duplicata de qualquer forma, mas assim devolvemos um resultado útil
    em vez de deixar estourar erro de integridade do banco.
    """
    employee = get_employee_by_user_id(user_id=user_id)
    if employee is None:
        raise EmployeeNotFoundError()

    service = get_service_by_id(service_id=data.service_id)
    if service is None:
        raise ServiceNotFound()

    existing = get_employee_service(employee_id=employee.id, service_id=data.service_id)
    if existing is not None:
        if existing.is_active:
            raise AssociationAlreadyExists()
        existing = activate_employee_service(existing)
        return EmployeeServicePrivateOut.from_orm(existing)

    association_created = create_employee_service(employee=employee, service=service)
    return EmployeeServicePrivateOut.from_orm(association_created)


def _get_own_employee_service(user_id: uuid.UUID, employee_service_id: uuid.UUID):
    """
    Resolve o Employee dono do vínculo e o EmployeeService pelo ID,
    garantindo que o vínculo pertence a esse funcionário.
    """
    employee = get_employee_by_user_id(user_id=user_id)
    if employee is None:
        raise EmployeeNotFoundError()

    employee_service = get_employee_service_by_id(employee_service_id=employee_service_id)
    if employee_service is None or employee_service.employee_id != employee.id:
        raise AssociationNotFound()

    return employee_service


def activate_employee_service_for_employee(user_id: uuid.UUID, employee_service_id: uuid.UUID) -> EmployeeServicePrivateOut:
    """Funcionário reativa um vínculo próprio que estava desativado."""
    employee_service = _get_own_employee_service(user_id, employee_service_id)
    employee_service = activate_employee_service(employee_service)
    return EmployeeServicePrivateOut.from_orm(employee_service)


def deactivate_employee_service_for_employee(user_id: uuid.UUID, employee_service_id: uuid.UUID) -> EmployeeServicePrivateOut:
    """
    Funcionário desativa um vínculo próprio (soft delete) — preserva o
    histórico de agendamentos feitos enquanto o vínculo estava ativo.
    """
    employee_service = _get_own_employee_service(user_id, employee_service_id)
    employee_service = deactivate_employee_service(employee_service)
    return EmployeeServicePrivateOut.from_orm(employee_service)


def delete_employee_service_for_employee(user_id: uuid.UUID, employee_service_id: uuid.UUID) -> None:
    """
    Funcionário exclui permanentemente um vínculo próprio.
    Use com cautela — prefira `deactivate_employee_service_for_employee` na
    maioria dos casos, já que isso apaga o registro do banco de vez.
    """
    employee_service = _get_own_employee_service(user_id, employee_service_id)
    delete_employee_service(employee_service)