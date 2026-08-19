"""
Rotas de EmployeeCommission (Comissões / repasse de funcionário).

- Admin: gera comissão (individual ou em lote por período), lista com
  filtros, edita valor pontualmente, atualiza status (individual ou em
  lote pro período inteiro) e exclui.
- Funcionário: só consulta as PRÓPRIAS comissões (sem escrita).
"""
from datetime import date
from typing import Optional
from uuid import UUID

from django_ratelimit.decorators import ratelimit
from ninja import Router

from beauty_formula.apps.accounts.models.user import User
from beauty_formula.apps.accounts.schemas.user_schema import MessageOut
from beauty_formula.apps.core.exceptions.payment_exception import (
    CommissionAlreadyExists,
    CommissionCannotBeModified,
    CommissionNotFound,
    SchedulingNotCompleted,
)
from beauty_formula.apps.core.exceptions.permissions import EmployeeNotFoundError
from beauty_formula.apps.core.exceptions.service_exception import SchedulingNotFound
from beauty_formula.apps.core.permissions.auth_classes import AdminOnlyAuth, EmployeeOnlyAuth
from beauty_formula.apps.core.utils.pagination import PAGE_SIZE_DEFAULT, PageOut, paginate_queryset
from beauty_formula.apps.payment.schemas.employee_commission_schema import (
    CommissionBulkGenerateIn,
    CommissionBulkGenerateOut,
    CommissionBulkStatusIn,
    CommissionBulkStatusOut,
    CommissionCreateIn,
    CommissionOut,
    CommissionStatusEnum,
    CommissionUpdateValueIn,
)
from beauty_formula.apps.payment.services.employee_commission_service import (
    cancel_commission_by_admin,
    create_commission_for_scheduling,
    delete_commission_by_admin,
    generate_commissions_for_period,
    get_commission_detail,
    get_own_commission_detail_for_employee,
    list_all_commissions,
    list_own_commissions_for_employee,
    mark_commission_as_paid_by_admin,
    update_commission_status_for_period,
    update_commission_value_by_admin,
)

router = Router()


# ═══════════════════════════════════════════════════════════════════════════════
# Admin — geração
# ═══════════════════════════════════════════════════════════════════════════════

@router.post(
    "/create",
    response={201: CommissionOut, 400: MessageOut, 404: MessageOut},
    auth=AdminOnlyAuth(),
    summary="Admin gera a comissão de UM atendimento concluído (valor calculado automaticamente)",
)
@ratelimit(key="user", rate="30/m", block=True)
def create_commission_router(request, payload: CommissionCreateIn):
    try:
        commission = create_commission_for_scheduling(payload)
        return 201, commission
    except SchedulingNotFound as e:
        return 404, {"detail": str(e)}
    except SchedulingNotCompleted as e:
        return 400, {"detail": str(e)}
    except CommissionAlreadyExists as e:
        return 400, {"detail": str(e)}
    except Exception as e:
        return 400, {"detail": str(e)}


@router.post(
    "/generate-period",
    response={201: CommissionBulkGenerateOut, 400: MessageOut},
    auth=AdminOnlyAuth(),
    summary="Admin gera as comissões de um período inteiro (todo COMPLETED sem comissão ainda)",
)
@ratelimit(key="user", rate="10/m", block=True)
def generate_commissions_for_period_router(request, payload: CommissionBulkGenerateIn):
    try:
        result = generate_commissions_for_period(payload)
        return 201, result
    except Exception as e:
        return 400, {"detail": str(e)}


# ═══════════════════════════════════════════════════════════════════════════════
# Admin — listagem / detalhe / edição pontual
# ═══════════════════════════════════════════════════════════════════════════════

@router.get(
    "/list-all",
    response={200: PageOut[CommissionOut], 400: MessageOut, 403: MessageOut},
    auth=AdminOnlyAuth(),
    summary="Admin lista todas as comissões, com filtros por funcionário/status/período",
)
@ratelimit(key="user", rate="30/m", block=True)
def list_all_commissions_router(
    request,
    page: int = 1,
    page_size: int = PAGE_SIZE_DEFAULT,
    employee_id: Optional[UUID] = None,
    status: Optional[CommissionStatusEnum] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
):
    try:
        commissions_qs = list_all_commissions(
            employee_id=employee_id,
            status=status.value if status else None,
            start_date=start_date,
            end_date=end_date,
        )
        result = paginate_queryset(commissions_qs, page, page_size, CommissionOut.from_orm)
        return 200, result
    except Exception as e:
        return 400, {"detail": str(e)}


@router.get(
    "/{commission_id}",
    response={200: CommissionOut, 400: MessageOut, 403: MessageOut, 404: MessageOut},
    auth=AdminOnlyAuth(),
    summary="Admin vê o detalhe de uma comissão",
)
@ratelimit(key="user", rate="30/m", block=True)
def get_commission_router(request, commission_id: UUID):
    try:
        commission = get_commission_detail(commission_id=commission_id)
        return 200, commission
    except CommissionNotFound as e:
        return 404, {"detail": str(e)}
    except Exception as e:
        return 400, {"detail": str(e)}


@router.patch(
    "/update-value/{commission_id}",
    response={200: CommissionOut, 400: MessageOut, 403: MessageOut, 404: MessageOut},
    auth=AdminOnlyAuth(),
    summary="Admin corrige manualmente o valor de uma comissão pendente (exceção à regra automática)",
)
@ratelimit(key="user", rate="20/m", block=True)
def update_commission_value_router(request, commission_id: UUID, payload: CommissionUpdateValueIn):
    try:
        commission = update_commission_value_by_admin(commission_id=commission_id, commission_value=payload.commission_value)
        return 200, commission
    except CommissionNotFound as e:
        return 404, {"detail": str(e)}
    except CommissionCannotBeModified as e:
        return 400, {"detail": str(e)}
    except Exception as e:
        return 400, {"detail": str(e)}


# ═══════════════════════════════════════════════════════════════════════════════
# Admin — status (individual e em lote)
# ═══════════════════════════════════════════════════════════════════════════════

@router.patch(
    "/mark-as-paid/{commission_id}",
    response={200: CommissionOut, 400: MessageOut, 403: MessageOut, 404: MessageOut},
    auth=AdminOnlyAuth(),
    summary="Admin confirma o repasse de UMA comissão",
)
@ratelimit(key="user", rate="30/m", block=True)
def mark_commission_as_paid_router(request, commission_id: UUID):
    try:
        commission = mark_commission_as_paid_by_admin(commission_id=commission_id)
        return 200, commission
    except CommissionNotFound as e:
        return 404, {"detail": str(e)}
    except CommissionCannotBeModified as e:
        return 400, {"detail": str(e)}
    except Exception as e:
        return 400, {"detail": str(e)}


@router.patch(
    "/cancel/{commission_id}",
    response={200: CommissionOut, 400: MessageOut, 403: MessageOut, 404: MessageOut},
    auth=AdminOnlyAuth(),
    summary="Admin cancela UMA comissão pendente",
)
@ratelimit(key="user", rate="20/m", block=True)
def cancel_commission_router(request, commission_id: UUID):
    try:
        commission = cancel_commission_by_admin(commission_id=commission_id)
        return 200, commission
    except CommissionNotFound as e:
        return 404, {"detail": str(e)}
    except CommissionCannotBeModified as e:
        return 400, {"detail": str(e)}
    except Exception as e:
        return 400, {"detail": str(e)}


@router.patch(
    "/update-status-period",
    response={200: CommissionBulkStatusOut, 400: MessageOut},
    auth=AdminOnlyAuth(),
    summary="Admin paga ou cancela de uma vez todas as comissões PENDING de um período",
)
@ratelimit(key="user", rate="10/m", block=True)
def update_commission_status_for_period_router(request, payload: CommissionBulkStatusIn):
    try:
        result = update_commission_status_for_period(payload)
        return 200, result
    except Exception as e:
        return 400, {"detail": str(e)}


@router.delete(
    "/{commission_id}",
    response={200: MessageOut, 400: MessageOut, 403: MessageOut, 404: MessageOut},
    auth=AdminOnlyAuth(),
    summary="Admin exclui permanentemente um registro de comissão",
)
@ratelimit(key="user", rate="10/m", block=True)
def delete_commission_router(request, commission_id: UUID):
    try:
        delete_commission_by_admin(commission_id=commission_id)
        return 200, {"detail": "Comissão excluída com sucesso."}
    except CommissionNotFound as e:
        return 404, {"detail": str(e)}
    except Exception as e:
        return 400, {"detail": str(e)}


# ═══════════════════════════════════════════════════════════════════════════════
# Funcionário — somente leitura
# ═══════════════════════════════════════════════════════════════════════════════

@router.get(
    "/my-commissions/list",
    response={200: PageOut[CommissionOut], 400: MessageOut, 403: MessageOut, 404: MessageOut},
    auth=EmployeeOnlyAuth(),
    summary="Funcionário lista as próprias comissões, com filtro por status/período",
)
@ratelimit(key="user", rate="30/m", block=True)
def list_my_commissions_router(
    request,
    page: int = 1,
    page_size: int = PAGE_SIZE_DEFAULT,
    status: Optional[CommissionStatusEnum] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
):
    user: User = request.auth
    try:
        commissions_qs = list_own_commissions_for_employee(
            user_id=user.id,
            status=status.value if status else None,
            start_date=start_date,
            end_date=end_date,
        )
        result = paginate_queryset(commissions_qs, page, page_size, CommissionOut.from_orm)
        return 200, result
    except EmployeeNotFoundError:
        return 404, {"detail": "Funcionário não encontrado."}
    except Exception as e:
        return 400, {"detail": str(e)}


@router.get(
    "/my-commissions/{commission_id}",
    response={200: CommissionOut, 400: MessageOut, 403: MessageOut, 404: MessageOut},
    auth=EmployeeOnlyAuth(),
    summary="Funcionário vê o detalhe de uma comissão própria",
)
@ratelimit(key="user", rate="30/m", block=True)
def get_my_commission_router(request, commission_id: UUID):
    user: User = request.auth
    try:
        commission = get_own_commission_detail_for_employee(user_id=user.id, commission_id=commission_id)
        return 200, commission
    except EmployeeNotFoundError:
        return 404, {"detail": "Funcionário não encontrado."}
    except CommissionNotFound as e:
        return 404, {"detail": str(e)}
    except Exception as e:
        return 400, {"detail": str(e)}