"""
Rotas de EmployeeTimeOff — funcionário gerencia os próprios bloqueios
de horário (recorrentes ou pontuais).
"""
import uuid
from datetime import date, datetime, time
from typing import List, Optional

from django.core.exceptions import ValidationError
from django_ratelimit.decorators import ratelimit
from ninja import Router

from beauty_formula.apps.accounts.models.user import User
from beauty_formula.apps.accounts.schemas.user_schema import MessageOut
from beauty_formula.apps.core.exceptions.permissions import EmployeeNotFoundError
from beauty_formula.apps.core.exceptions.service_exception import (
    TimeOffNotFound,
    TimeOffConflict,
    InvalidTimeOffRequest,
)
from beauty_formula.apps.core.permissions.auth_classes import EmployeeOnlyAuth
from beauty_formula.apps.core.utils.pagination import paginate_queryset, PageOut, PAGE_SIZE_DEFAULT
from beauty_formula.apps.services.schemas.employee_time_off_schema import (
    BlockTypeEnum,
    EmployeeTimeOffRecurringCreateIn,
    EmployeeTimeOffPunctualCreateIn,
    EmployeeTimeOffOut,
    EmployeeTimeOffUpdateIn,
    EmployeeTimeOffList,
)
from beauty_formula.apps.services.services.employee_time_off_service import (
    create_recurring_time_off_for_employee,
    create_punctual_time_off_for_employee,
    update_time_off_for_employee,
    delete_time_off_for_employee,
    delete_all_time_off_for_employee,
    delete_recurring_time_off_for_employee,
    delete_punctual_time_off_for_employee,
    delete_time_off_by_block_type_for_employee,
    list_own_time_off,
    list_own_recurring_time_off,
    list_own_punctual_time_off,
    list_own_time_off_by_block_type,
    list_own_time_off_on_date,
    list_own_time_off_date_range,
    list_own_active_time_off,
    list_own_upcoming_time_off,
)

router = Router()


# ═══════════════════════════════════════════════════════════════════════════════
# Listagens
# ═══════════════════════════════════════════════════════════════════════════════

@router.get(
    "/list-my-time-off",
    response={200: PageOut[EmployeeTimeOffOut], 400: MessageOut, 403: MessageOut, 404: MessageOut},
    auth=EmployeeOnlyAuth(),
    summary="Funcionário lista todos os próprios bloqueios de horário",
)
@ratelimit(key="user", rate="30/m", block=True)
def list_my_time_off_router(
    request, page: int = 1, page_size: int = PAGE_SIZE_DEFAULT
):
    """
    Lista TODOS os bloqueios do funcionário (recorrentes e pontuais).
    """
    user: User = request.auth

    try:
        time_off_qs = list_own_time_off(user_id=user.id)
        result = paginate_queryset(time_off_qs, page, page_size, lambda t: t)
        return 200, result
    except EmployeeNotFoundError:
        return 404, {"detail": "Funcionário não encontrado."}
    except Exception as e:
        return 400, {"detail": str(e)}


@router.get(
    "/list-my-recurring-time-off",
    response={200: PageOut[EmployeeTimeOffOut], 400: MessageOut, 403: MessageOut, 404: MessageOut},
    auth=EmployeeOnlyAuth(),
    summary="Funcionário lista apenas bloqueios recorrentes",
)
@ratelimit(key="user", rate="30/m", block=True)
def list_my_recurring_time_off_router(
    request, page: int = 1, page_size: int = PAGE_SIZE_DEFAULT
):
    """
    Lista apenas bloqueios recorrentes (weekday + start_time + end_time).
    """
    user: User = request.auth

    try:
        time_off_qs = list_own_recurring_time_off(user_id=user.id)
        result = paginate_queryset(time_off_qs, page, page_size, lambda t: t)
        return 200, result
    except EmployeeNotFoundError:
        return 404, {"detail": "Funcionário não encontrado."}
    except Exception as e:
        return 400, {"detail": str(e)}


@router.get(
    "/list-my-punctual-time-off",
    response={200: PageOut[EmployeeTimeOffOut], 400: MessageOut, 403: MessageOut, 404: MessageOut},
    auth=EmployeeOnlyAuth(),
    summary="Funcionário lista apenas bloqueios pontuais",
)
@ratelimit(key="user", rate="30/m", block=True)
def list_my_punctual_time_off_router(
    request, page: int = 1, page_size: int = PAGE_SIZE_DEFAULT
):
    """
    Lista apenas bloqueios pontuais (start_datetime + end_datetime).
    """
    user: User = request.auth

    try:
        time_off_qs = list_own_punctual_time_off(user_id=user.id)
        result = paginate_queryset(time_off_qs, page, page_size, lambda t: t)
        return 200, result
    except EmployeeNotFoundError:
        return 404, {"detail": "Funcionário não encontrado."}
    except Exception as e:
        return 400, {"detail": str(e)}


@router.get(
    "/list-my-time-off-by-block-type/{block_type}",
    response={200: PageOut[EmployeeTimeOffOut], 400: MessageOut, 403: MessageOut, 404: MessageOut},
    auth=EmployeeOnlyAuth(),
    summary="Funcionário lista bloqueios por tipo",
)
@ratelimit(key="user", rate="30/m", block=True)
def list_my_time_off_by_block_type_router(
    request, block_type: BlockTypeEnum, page: int = 1, page_size: int = PAGE_SIZE_DEFAULT
):
    """
    Lista bloqueios filtrados por tipo (ex: LUNCH, VACATION, etc).
    """
    user: User = request.auth

    try:
        time_off_qs = list_own_time_off_by_block_type(
            user_id=user.id,
            block_type=block_type.value
        )
        result = paginate_queryset(time_off_qs, page, page_size, lambda t: t)
        return 200, result
    except EmployeeNotFoundError:
        return 404, {"detail": "Funcionário não encontrado."}
    except Exception as e:
        return 400, {"detail": str(e)}


@router.get(
    "/list-my-time-off-on-date",
    response={200: PageOut[EmployeeTimeOffOut], 400: MessageOut, 403: MessageOut, 404: MessageOut},
    auth=EmployeeOnlyAuth(),
    summary="Funcionário lista bloqueios para uma data específica",
)
@ratelimit(key="user", rate="30/m", block=True)
def list_my_time_off_on_date_router(
    request, target_date: date, page: int = 1, page_size: int = PAGE_SIZE_DEFAULT
):
    """
    Lista bloqueios que afetam uma data específica (recorrentes + pontuais).
    """
    user: User = request.auth

    try:
        time_off_qs = list_own_time_off_on_date(
            user_id=user.id,
            target_date=target_date
        )
        result = paginate_queryset(time_off_qs, page, page_size, lambda t: t)
        return 200, result
    except EmployeeNotFoundError:
        return 404, {"detail": "Funcionário não encontrado."}
    except Exception as e:
        return 400, {"detail": str(e)}


@router.get(
    "/list-my-time-off-date-range",
    response={200: PageOut[EmployeeTimeOffOut], 400: MessageOut, 403: MessageOut, 404: MessageOut},
    auth=EmployeeOnlyAuth(),
    summary="Funcionário lista bloqueios em um período",
)
@ratelimit(key="user", rate="30/m", block=True)
def list_my_time_off_date_range_router(
    request,
    start_date: date,
    end_date: date,
    page: int = 1,
    page_size: int = PAGE_SIZE_DEFAULT
):
    """
    Lista bloqueios em um período de datas.
    """
    user: User = request.auth

    try:
        if start_date > end_date:
            return 400, {"detail": "start_date não pode ser maior que end_date."}

        time_off_qs = list_own_time_off_date_range(
            user_id=user.id,
            start_date=start_date,
            end_date=end_date
        )
        result = paginate_queryset(time_off_qs, page, page_size, lambda t: t)
        return 200, result
    except EmployeeNotFoundError:
        return 404, {"detail": "Funcionário não encontrado."}
    except Exception as e:
        return 400, {"detail": str(e)}


@router.get(
    "/list-my-active-time-off",
    response={200: PageOut[EmployeeTimeOffOut], 400: MessageOut, 403: MessageOut, 404: MessageOut},
    auth=EmployeeOnlyAuth(),
    summary="Funcionário lista bloqueios ativos no momento",
)
@ratelimit(key="user", rate="30/m", block=True)
def list_my_active_time_off_router(
    request, page: int = 1, page_size: int = PAGE_SIZE_DEFAULT
):
    """
    Lista bloqueios ativos no momento atual (considerando data/hora).
    """
    user: User = request.auth

    try:
        time_off_qs = list_own_active_time_off(user_id=user.id)
        result = paginate_queryset(time_off_qs, page, page_size, lambda t: t)
        return 200, result
    except EmployeeNotFoundError:
        return 404, {"detail": "Funcionário não encontrado."}
    except Exception as e:
        return 400, {"detail": str(e)}


@router.get(
    "/list-my-upcoming-time-off",
    response={200: PageOut[EmployeeTimeOffOut], 400: MessageOut, 403: MessageOut, 404: MessageOut},
    auth=EmployeeOnlyAuth(),
    summary="Funcionário lista bloqueios futuros",
)
@ratelimit(key="user", rate="30/m", block=True)
def list_my_upcoming_time_off_router(
    request,
    days_ahead: int = 7,
    page: int = 1,
    page_size: int = PAGE_SIZE_DEFAULT
):
    """
    Lista bloqueios futuros (próximos N dias).
    """
    user: User = request.auth

    try:
        if days_ahead < 1 or days_ahead > 90:
            return 400, {"detail": "days_ahead deve estar entre 1 e 90."}

        time_off_qs = list_own_upcoming_time_off(
            user_id=user.id,
            days_ahead=days_ahead
        )
        result = paginate_queryset(time_off_qs, page, page_size, lambda t: t)
        return 200, result
    except EmployeeNotFoundError:
        return 404, {"detail": "Funcionário não encontrado."}
    except Exception as e:
        return 400, {"detail": str(e)}


# ═══════════════════════════════════════════════════════════════════════════════
# Criação, Atualização e Deleção
# ═══════════════════════════════════════════════════════════════════════════════

@router.post(
    "/recurring/",
    response={201: EmployeeTimeOffOut, 400: MessageOut, 403: MessageOut, 404: MessageOut},
    auth=EmployeeOnlyAuth(),
    summary="Funcionário cria um bloqueio RECORRENTE",
)
@ratelimit(key="user", rate="30/m", block=True)
def create_recurring_time_off_router(request, payload: EmployeeTimeOffRecurringCreateIn):
    """
    Cria um bloqueio recorrente (ex: almoço toda terça, 12h-13h).
    Repete toda semana até ser editado ou excluído.
    """
    user: User = request.auth

    try:
        time_off = create_recurring_time_off_for_employee(
            user_id=user.id,
            block_type=payload.block_type.value,
            weekday=payload.weekday.value,
            start_time=payload.start_time,
            end_time=payload.end_time,
        )
        return 201, time_off
    except EmployeeNotFoundError:
        return 404, {"detail": "Funcionário não encontrado."}
    except ValidationError as e:
        return 400, {"detail": "; ".join(e.messages)}
    except Exception as e:
        return 400, {"detail": str(e)}


@router.post(
    "/punctual/",
    response={201: EmployeeTimeOffOut, 400: MessageOut, 403: MessageOut, 404: MessageOut},
    auth=EmployeeOnlyAuth(),
    summary="Funcionário cria um bloqueio PONTUAL",
)
@ratelimit(key="user", rate="30/m", block=True)
def create_punctual_time_off_router(request, payload: EmployeeTimeOffPunctualCreateIn):
    """
    Cria um bloqueio pontual (ex: consulta médica dia 15/08, 14h-15h).
    Expira sozinho (soft delete automático via Celery) 1 minuto depois
    de end_datetime.
    """
    user: User = request.auth

    try:
        time_off = create_punctual_time_off_for_employee(
            user_id=user.id,
            block_type=payload.block_type.value,
            start_datetime=payload.start_datetime,
            end_datetime=payload.end_datetime,
        )
        return 201, time_off
    except EmployeeNotFoundError:
        return 404, {"detail": "Funcionário não encontrado."}
    except TimeOffConflict as e:
        return 400, {"detail": str(e)}
    except ValidationError as e:
        return 400, {"detail": "; ".join(e.messages)}
    except Exception as e:
        return 400, {"detail": str(e)}


@router.patch(
    "/{time_off_id}",
    response={200: EmployeeTimeOffOut, 400: MessageOut, 403: MessageOut, 404: MessageOut},
    auth=EmployeeOnlyAuth(),
    summary="Funcionário atualiza um bloqueio próprio",
)
@ratelimit(key="user", rate="30/m", block=True)
def update_time_off_router(request, time_off_id: uuid.UUID, payload: EmployeeTimeOffUpdateIn):
    """
    Atualiza parcialmente um bloqueio próprio.
    """
    user: User = request.auth

    try:
        time_off = update_time_off_for_employee(
            user_id=user.id,
            time_off_id=time_off_id,
            block_type=payload.block_type.value if payload.block_type is not None else None,
            weekday=payload.weekday.value if payload.weekday is not None else None,
            start_time=payload.start_time,
            end_time=payload.end_time,
            start_datetime=payload.start_datetime,
            end_datetime=payload.end_datetime,
        )
        return 200, time_off
    except EmployeeNotFoundError:
        return 404, {"detail": "Funcionário não encontrado."}
    except TimeOffNotFound as e:
        return 404, {"detail": str(e)}
    except TimeOffConflict as e:
        return 400, {"detail": str(e)}
    except ValidationError as e:
        return 400, {"detail": "; ".join(e.messages)}
    except Exception as e:
        return 400, {"detail": str(e)}


@router.delete(
    "/{time_off_id}",
    response={200: MessageOut, 400: MessageOut, 403: MessageOut, 404: MessageOut},
    auth=EmployeeOnlyAuth(),
    summary="Funcionário exclui um bloqueio próprio",
)
@ratelimit(key="user", rate="30/m", block=True)
def delete_time_off_router(request, time_off_id: uuid.UUID):
    """
    Exclui permanentemente um bloqueio próprio.
    """
    user: User = request.auth

    try:
        delete_time_off_for_employee(user_id=user.id, time_off_id=time_off_id)
        return 200, {"detail": "Bloqueio excluído com sucesso."}
    except EmployeeNotFoundError:
        return 404, {"detail": "Funcionário não encontrado."}
    except TimeOffNotFound as e:
        return 404, {"detail": str(e)}
    except Exception as e:
        return 400, {"detail": str(e)}


@router.delete(
    "/delete-all",
    response={200: MessageOut, 400: MessageOut, 403: MessageOut, 404: MessageOut},
    auth=EmployeeOnlyAuth(),
    summary="Funcionário exclui todos os bloqueios",
)
@ratelimit(key="user", rate="30/m", block=True)
def delete_all_time_off_router(request):
    """
    Exclui permanentemente TODOS os bloqueios do funcionário.
    """
    user: User = request.auth

    try:
        delete_all_time_off_for_employee(user_id=user.id)
        return 200, {"detail": "Todos os bloqueios excluídos com sucesso."}
    except EmployeeNotFoundError:
        return 404, {"detail": "Funcionário não encontrado."}
    except Exception as e:
        return 400, {"detail": str(e)}


@router.delete(
    "/delete-recurring",
    response={200: MessageOut, 400: MessageOut, 403: MessageOut, 404: MessageOut},
    auth=EmployeeOnlyAuth(),
    summary="Funcionário exclui todos os bloqueios recorrentes",
)
@ratelimit(key="user", rate="30/m", block=True)
def delete_recurring_time_off_router(request):
    """
    Exclui permanentemente TODOS os bloqueios recorrentes do funcionário.
    """
    user: User = request.auth

    try:
        delete_recurring_time_off_for_employee(user_id=user.id)
        return 200, {"detail": "Todos os bloqueios recorrentes excluídos com sucesso."}
    except EmployeeNotFoundError:
        return 404, {"detail": "Funcionário não encontrado."}
    except Exception as e:
        return 400, {"detail": str(e)}


@router.delete(
    "/delete-punctual",
    response={200: MessageOut, 400: MessageOut, 403: MessageOut, 404: MessageOut},
    auth=EmployeeOnlyAuth(),
    summary="Funcionário exclui todos os bloqueios pontuais",
)
@ratelimit(key="user", rate="30/m", block=True)
def delete_punctual_time_off_router(request):
    """
    Exclui permanentemente TODOS os bloqueios pontuais do funcionário.
    """
    user: User = request.auth

    try:
        delete_punctual_time_off_for_employee(user_id=user.id)
        return 200, {"detail": "Todos os bloqueios pontuais excluídos com sucesso."}
    except EmployeeNotFoundError:
        return 404, {"detail": "Funcionário não encontrado."}
    except Exception as e:
        return 400, {"detail": str(e)}


@router.delete(
    "/delete-by-block-type/{block_type}",
    response={200: MessageOut, 400: MessageOut, 403: MessageOut, 404: MessageOut},
    auth=EmployeeOnlyAuth(),
    summary="Funcionário exclui bloqueios por tipo",
)
@ratelimit(key="user", rate="30/m", block=True)
def delete_time_off_by_block_type_router(request, block_type: BlockTypeEnum):
    """
    Exclui permanentemente TODOS os bloqueios do funcionário por tipo específico.
    """
    user: User = request.auth

    try:
        delete_time_off_by_block_type_for_employee(
            user_id=user.id,
            block_type=block_type.value
        )
        return 200, {"detail": f"Bloqueios do tipo {block_type.value} excluídos com sucesso."}
    except EmployeeNotFoundError:
        return 404, {"detail": "Funcionário não encontrado."}
    except Exception as e:
        return 400, {"detail": str(e)}