"""
Rotas de Scheduling (Agendamentos).

- Cliente: cria, lista, vê detalhe, edita observações, reagenda e cancela
  os próprios agendamentos.
- Funcionário: lista/vê os próprios agendamentos e conclui, marca não
  comparecimento ou cancela os que atende.
- Admin: visão total — lista com filtros, vê qualquer detalhe, edita,
  cancela e exclui permanentemente.

Sem confirmação manual nem status "em andamento": todo agendamento já
nasce CONFIRMED (a disponibilidade já foi validada na criação).
"""
from datetime import datetime
from typing import Optional
from uuid import UUID

from django_ratelimit.decorators import ratelimit
from ninja import Router

from beauty_formula.apps.accounts.models.user import User
from beauty_formula.apps.accounts.schemas.user_schema import MessageOut
from beauty_formula.apps.core.exceptions.permissions import ClientNotFoundError, EmployeeNotFoundError
from beauty_formula.apps.core.exceptions.service_exception import (
    AssociationNotFound,
    InvalidSchedulingStatusTransition,
    SchedulingCannotBeCanceled,
    SchedulingCannotBeModified,
    SchedulingConflict,
    SchedulingNotFound,
    ServiceNotFound,
)
from beauty_formula.apps.core.permissions.auth_classes import (
    AdminOnlyAuth,
    ClientOnlyAuth,
    EmployeeOnlyAuth,
)
from beauty_formula.apps.core.utils.pagination import PAGE_SIZE_DEFAULT, PageOut, paginate_queryset
from beauty_formula.apps.services.schemas.scheduling_schema import (
    SchedulingCancelIn,
    SchedulingCreateIn,
    SchedulingOut,
    SchedulingPrivateOut,
    SchedulingRescheduleIn,
    SchedulingStatusEnum,
    SchedulingUpdateIn,
)
from beauty_formula.apps.services.services.scheduling_service import (
    cancel_own_scheduling_as_client,
    cancel_scheduling_as_admin,
    cancel_scheduling_as_employee,
    complete_scheduling_for_employee,
    create_scheduling_for_client,
    delete_scheduling_by_admin,
    get_own_scheduling_detail_for_client,
    get_own_scheduling_detail_for_employee,
    get_scheduling_detail,
    list_all_schedulings,
    list_own_schedulings_for_client,
    list_own_schedulings_for_employee,
    mark_scheduling_as_no_show_for_employee,
    reschedule_own_scheduling_for_client,
    update_own_scheduling_for_client,
    update_scheduling_by_admin,
)

router = Router()


# ═══════════════════════════════════════════════════════════════════════════════
# Cliente
# ═══════════════════════════════════════════════════════════════════════════════

@router.post(
    "/create",
    response={201: SchedulingOut, 400: MessageOut, 403: MessageOut, 404: MessageOut},
    auth=ClientOnlyAuth(),
    summary="Cliente cria um novo agendamento",
)
@ratelimit(key="user", rate="20/m", block=True)
def create_scheduling_router(request, payload: SchedulingCreateIn):
    user: User = request.auth
    try:
        scheduling = create_scheduling_for_client(user_id=user.id, data=payload)
        return 201, scheduling
    except ClientNotFoundError:
        return 404, {"detail": "Cliente não encontrado."}
    except ServiceNotFound as e:
        return 404, {"detail": str(e)}
    except EmployeeNotFoundError:
        return 404, {"detail": "Funcionário não encontrado."}
    except AssociationNotFound as e:
        return 404, {"detail": str(e)}
    except SchedulingConflict as e:
        return 400, {"detail": str(e)}
    except Exception as e:
        return 400, {"detail": str(e)}


@router.get(
    "/list-my-schedulings",
    response={200: PageOut[SchedulingOut], 400: MessageOut, 403: MessageOut, 404: MessageOut},
    auth=ClientOnlyAuth(),
    summary="Cliente lista os próprios agendamentos",
)
@ratelimit(key="user", rate="30/m", block=True)
def list_my_schedulings_router(request, page: int = 1, page_size: int = PAGE_SIZE_DEFAULT, active_only: bool = False):
    user: User = request.auth
    try:
        schedulings_qs = list_own_schedulings_for_client(user_id=user.id, active_only=active_only)
        result = paginate_queryset(schedulings_qs, page, page_size, SchedulingOut.from_orm)
        return 200, result
    except ClientNotFoundError:
        return 404, {"detail": "Cliente não encontrado."}
    except Exception as e:
        return 400, {"detail": str(e)}


@router.get(
    "/my-schedulings/{scheduling_id}",
    response={200: SchedulingOut, 400: MessageOut, 403: MessageOut, 404: MessageOut},
    auth=ClientOnlyAuth(),
    summary="Cliente vê o detalhe de um agendamento próprio",
)
@ratelimit(key="user", rate="30/m", block=True)
def get_my_scheduling_router(request, scheduling_id: UUID):
    user: User = request.auth
    try:
        scheduling = get_own_scheduling_detail_for_client(user_id=user.id, scheduling_id=scheduling_id)
        return 200, scheduling
    except ClientNotFoundError:
        return 404, {"detail": "Cliente não encontrado."}
    except SchedulingNotFound as e:
        return 404, {"detail": str(e)}
    except Exception as e:
        return 400, {"detail": str(e)}


@router.patch(
    "/update-my-scheduling/{scheduling_id}",
    response={200: SchedulingOut, 400: MessageOut, 403: MessageOut, 404: MessageOut},
    auth=ClientOnlyAuth(),
    summary="Cliente edita observações de um agendamento confirmado",
)
@ratelimit(key="user", rate="20/m", block=True)
def update_my_scheduling_router(request, scheduling_id: UUID, payload: SchedulingUpdateIn):
    user: User = request.auth
    try:
        scheduling = update_own_scheduling_for_client(user_id=user.id, scheduling_id=scheduling_id, data=payload)
        return 200, scheduling
    except ClientNotFoundError:
        return 404, {"detail": "Cliente não encontrado."}
    except SchedulingNotFound as e:
        return 404, {"detail": str(e)}
    except SchedulingCannotBeModified as e:
        return 400, {"detail": str(e)}
    except Exception as e:
        return 400, {"detail": str(e)}


@router.patch(
    "/reschedule-my-scheduling/{scheduling_id}",
    response={200: SchedulingOut, 400: MessageOut, 403: MessageOut, 404: MessageOut},
    auth=ClientOnlyAuth(),
    summary="Cliente reagenda um agendamento confirmado (cria um novo registro)",
)
@ratelimit(key="user", rate="20/m", block=True)
def reschedule_my_scheduling_router(request, scheduling_id: UUID, payload: SchedulingRescheduleIn):
    user: User = request.auth
    try:
        scheduling = reschedule_own_scheduling_for_client(user_id=user.id, scheduling_id=scheduling_id, data=payload)
        return 200, scheduling
    except ClientNotFoundError:
        return 404, {"detail": "Cliente não encontrado."}
    except SchedulingNotFound as e:
        return 404, {"detail": str(e)}
    except ServiceNotFound as e:
        return 404, {"detail": str(e)}
    except EmployeeNotFoundError:
        return 404, {"detail": "Funcionário não encontrado."}
    except AssociationNotFound as e:
        return 404, {"detail": str(e)}
    except SchedulingCannotBeModified as e:
        return 400, {"detail": str(e)}
    except SchedulingConflict as e:
        return 400, {"detail": str(e)}
    except Exception as e:
        return 400, {"detail": str(e)}


@router.patch(
    "/cancel-my-scheduling/{scheduling_id}",
    response={200: SchedulingOut, 400: MessageOut, 403: MessageOut, 404: MessageOut},
    auth=ClientOnlyAuth(),
    summary="Cliente cancela um agendamento próprio (até 2h antes)",
)
@ratelimit(key="user", rate="20/m", block=True)
def cancel_my_scheduling_router(request, scheduling_id: UUID, payload: SchedulingCancelIn):
    user: User = request.auth
    try:
        scheduling = cancel_own_scheduling_as_client(user_id=user.id, scheduling_id=scheduling_id, reason=payload.reason)
        return 200, scheduling
    except ClientNotFoundError:
        return 404, {"detail": "Cliente não encontrado."}
    except SchedulingNotFound as e:
        return 404, {"detail": str(e)}
    except SchedulingCannotBeCanceled as e:
        return 400, {"detail": str(e)}
    except Exception as e:
        return 400, {"detail": str(e)}


# ═══════════════════════════════════════════════════════════════════════════════
# Funcionário
# ═══════════════════════════════════════════════════════════════════════════════

@router.get(
    "/list-employee-schedulings",
    response={200: PageOut[SchedulingOut], 400: MessageOut, 403: MessageOut, 404: MessageOut},
    auth=EmployeeOnlyAuth(),
    summary="Funcionário lista os próprios agendamentos",
)
@ratelimit(key="user", rate="30/m", block=True)
def list_employee_schedulings_router(
    request, page: int = 1, page_size: int = PAGE_SIZE_DEFAULT, active_only: bool = False
):
    user: User = request.auth
    try:
        schedulings_qs = list_own_schedulings_for_employee(user_id=user.id, active_only=active_only)
        result = paginate_queryset(schedulings_qs, page, page_size, SchedulingOut.from_orm)
        return 200, result
    except EmployeeNotFoundError:
        return 404, {"detail": "Funcionário não encontrado."}
    except Exception as e:
        return 400, {"detail": str(e)}


@router.get(
    "/employee-schedulings/{scheduling_id}",
    response={200: SchedulingOut, 400: MessageOut, 403: MessageOut, 404: MessageOut},
    auth=EmployeeOnlyAuth(),
    summary="Funcionário vê o detalhe de um agendamento próprio",
)
@ratelimit(key="user", rate="30/m", block=True)
def get_employee_scheduling_router(request, scheduling_id: UUID):
    user: User = request.auth
    try:
        scheduling = get_own_scheduling_detail_for_employee(user_id=user.id, scheduling_id=scheduling_id)
        return 200, scheduling
    except EmployeeNotFoundError:
        return 404, {"detail": "Funcionário não encontrado."}
    except SchedulingNotFound as e:
        return 404, {"detail": str(e)}
    except Exception as e:
        return 400, {"detail": str(e)}


@router.patch(
    "/complete/{scheduling_id}",
    response={200: SchedulingOut, 400: MessageOut, 403: MessageOut, 404: MessageOut},
    auth=EmployeeOnlyAuth(),
    summary="Funcionário conclui um atendimento confirmado",
)
@ratelimit(key="user", rate="30/m", block=True)
def complete_scheduling_router(request, scheduling_id: UUID):
    user: User = request.auth
    try:
        scheduling = complete_scheduling_for_employee(user_id=user.id, scheduling_id=scheduling_id)
        return 200, scheduling
    except EmployeeNotFoundError:
        return 404, {"detail": "Funcionário não encontrado."}
    except SchedulingNotFound as e:
        return 404, {"detail": str(e)}
    except InvalidSchedulingStatusTransition as e:
        return 400, {"detail": str(e)}
    except Exception as e:
        return 400, {"detail": str(e)}


@router.patch(
    "/no-show/{scheduling_id}",
    response={200: SchedulingOut, 400: MessageOut, 403: MessageOut, 404: MessageOut},
    auth=EmployeeOnlyAuth(),
    summary="Funcionário marca um agendamento como não comparecido",
)
@ratelimit(key="user", rate="30/m", block=True)
def mark_no_show_router(request, scheduling_id: UUID):
    user: User = request.auth
    try:
        scheduling = mark_scheduling_as_no_show_for_employee(user_id=user.id, scheduling_id=scheduling_id)
        return 200, scheduling
    except EmployeeNotFoundError:
        return 404, {"detail": "Funcionário não encontrado."}
    except SchedulingNotFound as e:
        return 404, {"detail": str(e)}
    except InvalidSchedulingStatusTransition as e:
        return 400, {"detail": str(e)}
    except Exception as e:
        return 400, {"detail": str(e)}


@router.patch(
    "/cancel-employee-scheduling/{scheduling_id}",
    response={200: SchedulingOut, 400: MessageOut, 403: MessageOut, 404: MessageOut},
    auth=EmployeeOnlyAuth(),
    summary="Funcionário cancela um agendamento próprio",
)
@ratelimit(key="user", rate="20/m", block=True)
def cancel_employee_scheduling_router(request, scheduling_id: UUID, payload: SchedulingCancelIn):
    user: User = request.auth
    try:
        scheduling = cancel_scheduling_as_employee(user_id=user.id, scheduling_id=scheduling_id, reason=payload.reason)
        return 200, scheduling
    except EmployeeNotFoundError:
        return 404, {"detail": "Funcionário não encontrado."}
    except SchedulingNotFound as e:
        return 404, {"detail": str(e)}
    except SchedulingCannotBeCanceled as e:
        return 400, {"detail": str(e)}
    except Exception as e:
        return 400, {"detail": str(e)}


# ═══════════════════════════════════════════════════════════════════════════════
# Admin
# ═══════════════════════════════════════════════════════════════════════════════

@router.get(
    "/list-all",
    response={200: PageOut[SchedulingPrivateOut], 400: MessageOut, 403: MessageOut},
    auth=AdminOnlyAuth(),
    summary="Admin lista todos os agendamentos, com filtros combináveis",
)
@ratelimit(key="user", rate="30/m", block=True)
def list_all_schedulings_router(
    request,
    page: int = 1,
    page_size: int = PAGE_SIZE_DEFAULT,
    service_id: Optional[UUID] = None,
    employee_id: Optional[UUID] = None,
    client_id: Optional[UUID] = None,
    status: Optional[SchedulingStatusEnum] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    is_active: Optional[bool] = None,
):
    try:
        schedulings_qs = list_all_schedulings(
            service_id=service_id,
            employee_id=employee_id,
            client_id=client_id,
            status=status.value if status else None,
            start_date=start_date,
            end_date=end_date,
            is_active=is_active,
        )
        result = paginate_queryset(schedulings_qs, page, page_size, SchedulingPrivateOut.from_orm)
        return 200, result
    except Exception as e:
        return 400, {"detail": str(e)}


@router.get(
    "/{scheduling_id}",
    response={200: SchedulingPrivateOut, 400: MessageOut, 403: MessageOut, 404: MessageOut},
    auth=AdminOnlyAuth(),
    summary="Admin vê o detalhe completo de qualquer agendamento",
)
@ratelimit(key="user", rate="30/m", block=True)
def get_scheduling_router(request, scheduling_id: UUID):
    try:
        scheduling = get_scheduling_detail(scheduling_id=scheduling_id)
        return 200, scheduling
    except SchedulingNotFound as e:
        return 404, {"detail": str(e)}
    except Exception as e:
        return 400, {"detail": str(e)}


@router.patch(
    "/update/{scheduling_id}",
    response={200: SchedulingPrivateOut, 400: MessageOut, 403: MessageOut, 404: MessageOut},
    auth=AdminOnlyAuth(),
    summary="Admin edita qualquer agendamento que não esteja em status final",
)
@ratelimit(key="user", rate="20/m", block=True)
def update_scheduling_router(request, scheduling_id: UUID, payload: SchedulingUpdateIn):
    try:
        scheduling = update_scheduling_by_admin(scheduling_id=scheduling_id, data=payload)
        return 200, scheduling
    except SchedulingNotFound as e:
        return 404, {"detail": str(e)}
    except ServiceNotFound as e:
        return 404, {"detail": str(e)}
    except EmployeeNotFoundError:
        return 404, {"detail": "Funcionário não encontrado."}
    except AssociationNotFound as e:
        return 404, {"detail": str(e)}
    except SchedulingCannotBeModified as e:
        return 400, {"detail": str(e)}
    except SchedulingConflict as e:
        return 400, {"detail": str(e)}
    except Exception as e:
        return 400, {"detail": str(e)}


@router.patch(
    "/cancel/{scheduling_id}",
    response={200: SchedulingPrivateOut, 400: MessageOut, 403: MessageOut, 404: MessageOut},
    auth=AdminOnlyAuth(),
    summary="Admin cancela qualquer agendamento",
)
@ratelimit(key="user", rate="20/m", block=True)
def cancel_scheduling_router(request, scheduling_id: UUID, payload: SchedulingCancelIn):
    user: User = request.auth
    try:
        scheduling = cancel_scheduling_as_admin(user=user, scheduling_id=scheduling_id, reason=payload.reason)
        return 200, scheduling
    except SchedulingNotFound as e:
        return 404, {"detail": str(e)}
    except SchedulingCannotBeCanceled as e:
        return 400, {"detail": str(e)}
    except Exception as e:
        return 400, {"detail": str(e)}


@router.delete(
    "/{scheduling_id}",
    response={200: MessageOut, 400: MessageOut, 403: MessageOut, 404: MessageOut},
    auth=AdminOnlyAuth(),
    summary="Admin exclui permanentemente um agendamento",
)
@ratelimit(key="user", rate="10/m", block=True)
def delete_scheduling_router(request, scheduling_id: UUID):
    try:
        delete_scheduling_by_admin(scheduling_id=scheduling_id)
        return 200, {"detail": "Agendamento excluído com sucesso."}
    except SchedulingNotFound as e:
        return 404, {"detail": str(e)}
    except Exception as e:
        return 400, {"detail": str(e)}