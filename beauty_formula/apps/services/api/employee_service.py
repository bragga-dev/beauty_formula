"""
Rotas de EmployeeService — funcionário gerencia os próprios serviços atendidos.
"""
import uuid

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
    activate_employee_service_for_employee,
    deactivate_employee_service_for_employee,
    delete_employee_service_for_employee,
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

    try:
        employee_service = create_employee_service_for_employee(user_id=user.id, data=payload)
        return 201, employee_service
    except EmployeeNotFoundError:
        return 404, {"detail": "Funcionário não encontrado."}
    except ServiceNotFound as e:
        return 404, {"detail": str(e)}
    except AssociationAlreadyExists as e:
        return 400, {"detail": str(e)}
    except Exception as e:
        return 400, {"detail": str(e)}


@router.patch(
    "/activate-employee-service/{employee_service_id}",
    response={200: EmployeeServicePrivateOut, 400: MessageOut, 403: MessageOut, 404: MessageOut},
    auth=EmployeeOnlyAuth(),
    summary="Funcionário reativa um vínculo de serviço desativado",
)
@ratelimit(key="user", rate="30/m", block=True)
def activate_employee_service_router(request, employee_service_id: uuid.UUID):
    user: User = request.auth

    try:
        employee_service = activate_employee_service_for_employee(
            user_id=user.id, employee_service_id=employee_service_id
        )
        return 200, employee_service
    except EmployeeNotFoundError:
        return 404, {"detail": "Funcionário não encontrado."}
    except AssociationNotFound as e:
        return 404, {"detail": str(e)}
    except Exception as e:
        return 400, {"detail": str(e)}


@router.patch(
    "/deactivate-employee-service/{employee_service_id}",
    response={200: EmployeeServicePrivateOut, 400: MessageOut, 403: MessageOut, 404: MessageOut},
    auth=EmployeeOnlyAuth(),
    summary="Funcionário desativa um vínculo de serviço (soft delete)",
)
@ratelimit(key="user", rate="30/m", block=True)
def deactivate_employee_service_router(request, employee_service_id: uuid.UUID):
    user: User = request.auth

    try:
        employee_service = deactivate_employee_service_for_employee(
            user_id=user.id, employee_service_id=employee_service_id
        )
        return 200, employee_service
    except EmployeeNotFoundError:
        return 404, {"detail": "Funcionário não encontrado."}
    except AssociationNotFound as e:
        return 404, {"detail": str(e)}
    except Exception as e:
        return 400, {"detail": str(e)}


@router.delete(
    "/delete-employee-service/{employee_service_id}",
    response={200: MessageOut, 400: MessageOut, 403: MessageOut, 404: MessageOut},
    auth=EmployeeOnlyAuth(),
    summary="Funcionário exclui permanentemente um vínculo de serviço",
)
@ratelimit(key="user", rate="30/m", block=True)
def delete_employee_service_router(request, employee_service_id: uuid.UUID):
    user: User = request.auth

    try:
        delete_employee_service_for_employee(user_id=user.id, employee_service_id=employee_service_id)
        return 200, {"detail": "Vínculo excluído com sucesso."}
    except EmployeeNotFoundError:
        return 404, {"detail": "Funcionário não encontrado."}
    except AssociationNotFound as e:
        return 404, {"detail": str(e)}
    except Exception as e:
        return 400, {"detail": str(e)}