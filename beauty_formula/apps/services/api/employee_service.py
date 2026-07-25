"""
Rotas de EmployeeService — funcionário gerencia os próprios serviços atendidos.
"""
from django_ratelimit.decorators import ratelimit
from ninja import Router

from beauty_formula.apps.accounts.models.user import User
from beauty_formula.apps.accounts.selectors.employee_selector import get_employee_by_user_id
from beauty_formula.apps.accounts.schemas.user_schema import MessageOut
from beauty_formula.apps.core.exceptions.permissions import EmployeeNotFoundError
from beauty_formula.apps.core.exceptions.service_exception import (
    AssociationAlreadyExists,
    AssociationNotFound,
    ServiceNotFound,
)
from beauty_formula.apps.core.permissions.auth_classes import EmployeeOnlyAuth
from beauty_formula.apps.services.schemas.employee_service_schema import (
    EmployeeServiceCreateIn,
    EmployeeServicePrivateOut,
)
from beauty_formula.apps.services.services.employee_service_service import (
    create_employee_service_for_employee,
)

router = Router()


@router.post(
    "/create-employee-service",
    response={201: EmployeeServicePrivateOut, 400: MessageOut, 403: MessageOut, 404: MessageOut},
    auth=EmployeeOnlyAuth(),
    summary="Funcionário vincula um serviço que passa a atender",
)
@ratelimit(key="user", rate="30/m", block=True)
def create_employee_service_router(request, payload: EmployeeServiceCreateIn):
    user: User = request.auth

    employee = get_employee_by_user_id(user.id)
    if employee is None:
        return 404, {"detail": "Perfil de funcionário não encontrado para este usuário."}

    try:
        employee_service = create_employee_service_for_employee(employee.id, payload)
        return 201, employee_service
    except EmployeeNotFoundError:
        return 404, {"detail": "Funcionário não encontrado."}
    except ServiceNotFound as e:
        return 404, {"detail": str(e)}
    except AssociationAlreadyExists as e:
        return 400, {"detail": str(e)}
    except Exception as e:
        return 400, {"detail": str(e)}