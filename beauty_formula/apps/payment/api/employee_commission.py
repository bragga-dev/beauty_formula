"""
Rotas de EmployeeCommission (Comissões / repasse de funcionário).

- Admin: gera comissão (individual ou em lote por período), lista com
  filtros, vê o total por status, edita valor pontualmente, atualiza
  status (individual, em lote por seleção ou em lote pro período
  inteiro) e reverte um pagamento feito por engano.
- Funcionário: só consulta as PRÓPRIAS comissões e o próprio total (sem
  escrita).
- Não existe exclusão: comissão é um registro financeiro e precisa
  continuar auditável mesmo cancelada — o estado "CANCELED" cobre o
  caso de invalidar uma comissão sem apagar o histórico.
"""
from datetime import date
from typing import List, Optional
from uuid import UUID

from django_ratelimit.decorators import ratelimit
from ninja import Router

from beauty_formula.apps.accounts.models.user import User
from beauty_formula.apps.accounts.schemas.user_schema import MessageOut
from beauty_formula.apps.core.exceptions.payment_exception import (
    CommissionAlreadyExists,
    CommissionCannotBeModified,
    CommissionNotFound,
    CommissionNotPaid,
    SchedulingNotCompleted,
)
from beauty_formula.apps.core.exceptions.permissions import EmployeeNotFoundError
from beauty_formula.apps.core.exceptions.service_exception import SchedulingNotFound
from beauty_formula.apps.core.permissions.auth_classes import AdminOnlyAuth, EmployeeOnlyAuth
from beauty_formula.apps.core.utils.pagination import PAGE_SIZE_DEFAULT, PageOut, paginate_queryset
from beauty_formula.apps.payment.schemas.employee_commission_schema import (
    CommissionBulkGenerateIn,
    CommissionBulkGenerateOut,
    CommissionBulkMarkPaidIn,
    CommissionBulkMarkPaidOut,
    CommissionBulkStatusIn,
    CommissionBulkStatusOut,
    CommissionCreateIn,
    CommissionOut,
    CommissionStatusEnum,
    CommissionTotalsOut,
    CommissionUpdateCompetenciaIn,
    CommissionUpdateValueIn,
)
from beauty_formula.apps.payment.services.employee_commission_service import (
    cancel_commission_by_admin,
    create_commission_for_scheduling,
    generate_commissions_for_period,
    get_available_competencias_for_admin,
    get_commission_detail,
    get_commission_totals_for_admin,
    get_own_commission_detail_for_employee,
    get_own_commission_totals_for_employee,
    list_all_commissions,
    list_own_commissions_for_employee,
    mark_commission_as_paid_by_admin,
    mark_commissions_as_paid_by_ids,
    revert_commission_to_pending_by_admin,
    update_commission_competencia_by_admin,
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
    competencia: Optional[date] = None,
):
    try:
        commissions_qs = list_all_commissions(
            employee_id=employee_id,
            status=status.value if status else None,
            start_date=start_date,
            end_date=end_date,
            competencia=competencia,
        )
        result = paginate_queryset(commissions_qs, page, page_size, CommissionOut.from_orm)
        return 200, result
    except Exception as e:
        return 400, {"detail": str(e)}


@router.get(
    "/summary",
    response={200: CommissionTotalsOut, 400: MessageOut},
    auth=AdminOnlyAuth(),
    summary="Admin vê a soma das comissões por status (pendente/paga/cancelada), com os mesmos filtros da listagem",
)
@ratelimit(key="user", rate="30/m", block=True)
def get_commission_totals_router(
    request,
    employee_id: Optional[UUID] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    competencia: Optional[date] = None,
):
    try:
        totals = get_commission_totals_for_admin(
            employee_id=employee_id, start_date=start_date, end_date=end_date, competencia=competencia
        )
        return 200, totals
    except Exception as e:
        return 400, {"detail": str(e)}


@router.get(
    "/competencias",
    response={200: List[date], 400: MessageOut},
    auth=AdminOnlyAuth(),
    summary="Admin vê os meses de competência que realmente têm comissão (pra popular o filtro dinamicamente)",
    description=(
        "Lista, mais recente primeiro, os meses (dia 1) em que existe ao "
        "menos uma comissão — filtrado por funcionário se informado. Usado "
        "pra montar o dropdown de filtro de competência só com "
        "ano/mês que existem de verdade, em vez de um intervalo fixo "
        "arbitrário."
    ),
)
@ratelimit(key="user", rate="30/m", block=True)
def get_available_competencias_router(request, employee_id: Optional[UUID] = None):
    try:
        competencias = get_available_competencias_for_admin(employee_id=employee_id)
        return 200, competencias
    except Exception as e:
        return 400, {"detail": str(e)}


@router.get(
    # 'uuid:' aqui é essencial: sem ele o Django Ninja registra esse
    # segmento como string genérica (aceita qualquer texto), e por essa
    # rota vir ANTES de "/mark-as-paid-bulk" e "/update-status-period"
    # no arquivo, ela "sequestrava" essas duas rotas — o Django resolvia
    # a URL pra cá primeiro, via GET (única aceita aqui), e devolvia 405
    # pra qualquer PATCH endereçado a elas. Com 'uuid:', esse segmento só
    # casa com um UUID de verdade, e strings como "mark-as-paid-bulk"
    # passam pra frente até achar a rota literal certa. (Atenção à ordem:
    # "{uuid:commission_id}" — Ninja só troca "{ }" por "< >", então o
    # tipo tem que vir primeiro, igual a sintaxe nativa do Django.)
    "/{uuid:commission_id}",
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
    "/update-value/{uuid:commission_id}",
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


@router.patch(
    "/update-competencia/{uuid:commission_id}",
    response={200: CommissionOut, 400: MessageOut, 403: MessageOut, 404: MessageOut},
    auth=AdminOnlyAuth(),
    summary="Admin corrige manualmente o mês de competência de uma comissão (qualquer status)",
    description=(
        "Reclassifica em qual mês a comissão entra nos relatórios de "
        "auditoria. Não afeta valor nem repasse — por isso funciona "
        "mesmo em comissões já pagas ou canceladas. O valor calculado "
        "automaticamente na criação fica preservado em "
        "`competencia_original` pra sempre dar pra ver se e quanto foi "
        "ajustado manualmente."
    ),
)
@ratelimit(key="user", rate="20/m", block=True)
def update_commission_competencia_router(request, commission_id: UUID, payload: CommissionUpdateCompetenciaIn):
    user: User = request.auth
    try:
        commission = update_commission_competencia_by_admin(
            commission_id=commission_id, competencia=payload.competencia, changed_by=user
        )
        return 200, commission
    except CommissionNotFound as e:
        return 404, {"detail": str(e)}
    except Exception as e:
        return 400, {"detail": str(e)}


# ═══════════════════════════════════════════════════════════════════════════════
# Admin — status (individual e em lote)
# ═══════════════════════════════════════════════════════════════════════════════

@router.patch(
    "/mark-as-paid/{uuid:commission_id}",
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
    "/mark-as-paid-bulk",
    response={200: CommissionBulkMarkPaidOut, 400: MessageOut},
    auth=AdminOnlyAuth(),
    summary="Admin marca como pagas VÁRIAS comissões escolhidas manualmente (seleção na tabela)",
)
@ratelimit(key="user", rate="15/m", block=True)
def mark_commissions_as_paid_bulk_router(request, payload: CommissionBulkMarkPaidIn):
    try:
        result = mark_commissions_as_paid_by_ids(payload)
        return 200, result
    except Exception as e:
        return 400, {"detail": str(e)}


@router.patch(
    "/revert-to-pending/{uuid:commission_id}",
    response={200: CommissionOut, 400: MessageOut, 403: MessageOut, 404: MessageOut},
    auth=AdminOnlyAuth(),
    summary="Admin reverte UMA comissão paga por engano de volta pra pendente",
)
@ratelimit(key="user", rate="20/m", block=True)
def revert_commission_to_pending_router(request, commission_id: UUID):
    try:
        commission = revert_commission_to_pending_by_admin(commission_id=commission_id)
        return 200, commission
    except CommissionNotFound as e:
        return 404, {"detail": str(e)}
    except CommissionNotPaid as e:
        return 400, {"detail": str(e)}
    except Exception as e:
        return 400, {"detail": str(e)}


@router.patch(
    "/cancel/{uuid:commission_id}",
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


# ═══════════════════════════════════════════════════════════════════════════════
# Funcionário — somente leitura
# ═══════════════════════════════════════════════════════════════════════════════

@router.get(
    "/my-commissions/summary",
    response={200: CommissionTotalsOut, 400: MessageOut, 404: MessageOut},
    auth=EmployeeOnlyAuth(),
    summary="Funcionário vê a soma das próprias comissões por status",
)
@ratelimit(key="user", rate="30/m", block=True)
def get_my_commission_totals_router(
    request,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
):
    user: User = request.auth
    try:
        totals = get_own_commission_totals_for_employee(user_id=user.id, start_date=start_date, end_date=end_date)
        return 200, totals
    except EmployeeNotFoundError:
        return 404, {"detail": "Funcionário não encontrado."}
    except Exception as e:
        return 400, {"detail": str(e)}


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
    "/my-commissions/{uuid:commission_id}",
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