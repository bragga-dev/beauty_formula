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