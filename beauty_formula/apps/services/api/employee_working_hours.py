"""
Rotas de EmployeeWorkingHours — funcionário cadastra/gerencia os
próprios turnos de trabalho.
"""
import uuid
from typing import List

from django.core.exceptions import ValidationError
from django_ratelimit.decorators import ratelimit
from ninja import Router

from beauty_formula.apps.accounts.models.user import User
from beauty_formula.apps.accounts.schemas.user_schema import MessageOut
from beauty_formula.apps.core.exceptions.permissions import EmployeeNotFoundError
from beauty_formula.apps.core.exceptions.service_exception import WorkingHoursNotFound
from beauty_formula.apps.core.permissions.auth_classes import EmployeeOnlyAuth
from beauty_formula.apps.services.schemas.employee_working_hours_schema import (
    EmployeeWorkingHoursCreateIn,
    EmployeeWorkingHoursOut,
    EmployeeWorkingHoursUpdateIn,
)
from beauty_formula.apps.services.services.employee_working_hours_service import (
    create_working_hours_for_employee,
    delete_working_hours_for_employee,
    list_own_working_hours,
    update_working_hours_for_employee,
)

router = Router()


@router.get(
    "/list-my-working-hours",
    response={200: List[EmployeeWorkingHoursOut], 400: MessageOut, 404: MessageOut},
    auth=EmployeeOnlyAuth(),
    summary="Funcionário lista a própria grade de horários (semana inteira)",
)
@ratelimit(key="user", rate="30/m", block=True)
def list_my_working_hours_router(request):
    user: User = request.auth

    try:
        working_hours = list_own_working_hours(user_id=user.id)
        return 200, list(working_hours)
    except EmployeeNotFoundError:
        return 404, {"detail": "Funcionário não encontrado."}
    except Exception as e:
        return 400, {"detail": str(e)}


@router.post(
    "/",
    response={201: EmployeeWorkingHoursOut, 400: MessageOut, 404: MessageOut},
    auth=EmployeeOnlyAuth(),
    summary="Funcionário cadastra um turno de trabalho",
)
@ratelimit(key="user", rate="30/m", block=True)
def create_working_hours_router(request, payload: EmployeeWorkingHoursCreateIn):
    user: User = request.auth

    try:
        working_hours = create_working_hours_for_employee(
            user_id=user.id,
            weekday=payload.weekday.value,
            start_time=payload.start_time,
            end_time=payload.end_time,
        )
        return 201, working_hours
    except EmployeeNotFoundError:
        return 404, {"detail": "Funcionário não encontrado."}
    except ValidationError as e:
        return 400, {"detail": "; ".join(e.messages)}
    except Exception as e:
        return 400, {"detail": str(e)}


@router.patch(
    "/{working_hours_id}",
    response={200: EmployeeWorkingHoursOut, 400: MessageOut, 404: MessageOut},
    auth=EmployeeOnlyAuth(),
    summary="Funcionário edita um turno próprio",
)
@ratelimit(key="user", rate="30/m", block=True)
def update_working_hours_router(request, working_hours_id: uuid.UUID, payload: EmployeeWorkingHoursUpdateIn):
    user: User = request.auth

    try:
        working_hours = update_working_hours_for_employee(
            user_id=user.id,
            working_hours_id=working_hours_id,
            weekday=payload.weekday.value if payload.weekday is not None else None,
            start_time=payload.start_time,
            end_time=payload.end_time,
        )
        return 200, working_hours
    except EmployeeNotFoundError:
        return 404, {"detail": "Funcionário não encontrado."}
    except WorkingHoursNotFound as e:
        return 404, {"detail": str(e)}
    except ValidationError as e:
        return 400, {"detail": "; ".join(e.messages)}
    except Exception as e:
        return 400, {"detail": str(e)}


@router.delete(
    "/{working_hours_id}",
    response={200: MessageOut, 400: MessageOut, 404: MessageOut},
    auth=EmployeeOnlyAuth(),
    summary="Funcionário exclui um turno próprio",
)
@ratelimit(key="user", rate="30/m", block=True)
def delete_working_hours_router(request, working_hours_id: uuid.UUID):
    user: User = request.auth

    try:
        delete_working_hours_for_employee(user_id=user.id, working_hours_id=working_hours_id)
        return 200, {"detail": "Turno excluído com sucesso."}
    except EmployeeNotFoundError:
        return 404, {"detail": "Funcionário não encontrado."}
    except WorkingHoursNotFound as e:
        return 404, {"detail": str(e)}
    except Exception as e:
        return 400, {"detail": str(e)}