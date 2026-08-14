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
from beauty_formula.apps.core.utils.pagination import paginate_queryset, PageOut, PAGE_SIZE_DEFAULT
from beauty_formula.apps.services.schemas.employee_service_schema import (
    EmployeeServiceCreateIn,
    EmployeeServiceOut,
    EmployeeServicePrivateOut,
)
from beauty_formula.apps.services.services.employee_service_service import (
    create_employee_service_for_employee,
    activate_employee_service_for_employee,
    deactivate_employee_service_for_employee,
    delete_employee_service_for_employee,
    list_own_employee_services,
)

router = Router()


@router.get(
    "/list-my-services",
    response={200: PageOut[EmployeeServiceOut], 400: MessageOut, 403: MessageOut, 404: MessageOut},
    auth=EmployeeOnlyAuth(),
    summary="Funcionário lista os próprios vínculos de serviço (ativos e inativos)",
)
@ratelimit(key="user", rate="30/m", block=True)
def list_my_employee_services_router(
    request, page: int = 1, page_size: int = PAGE_SIZE_DEFAULT, active_only: bool = False
):
    """
    Lista TODOS os atributos de cada vínculo (incluindo is_active),
    já que o próprio funcionário precisa enxergar o estado de cada
    serviço pra decidir se ativa, desativa ou exclui. `active_only=True`
    filtra só os ativos, se o client quiser.
    """
    user: User = request.auth

    try:
        services_qs = list_own_employee_services(user_id=user.id, active_only=active_only)
        result = paginate_queryset(services_qs, page, page_size, lambda es: es)
        return 200, result
    except EmployeeNotFoundError:
        return 404, {"detail": "Funcionário não encontrado."}
    except Exception as e:
        return 400, {"detail": str(e)}


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