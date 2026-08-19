"""
Regras de negócio de EmployeeCommission.

- Só admin gerencia comissões (criação individual, geração em lote,
  edição manual de valor, atualização de status em lote, exclusão) — é
  o repasse financeiro pro funcionário, não uma ação que ele mesmo
  dispara.
- Funcionário só consulta as PRÓPRIAS comissões (somente leitura).
- Uma comissão só existe para um Scheduling COMPLETED; o funcionário é
  sempre `scheduling.employee`, nunca um valor à parte vindo do payload.
- O valor é sempre calculado automaticamente:
      price_at_booking * service.commission_percentage / 100
  (o `commission_percentage` do Service já é 70% por padrão). Só existe
  edição manual pontual (`update_commission_value_by_admin`) pra
  corrigir um caso excepcional depois de gerado.
- Geração em lote é idempotente: rodar de novo pro mesmo período/
  funcionário não duplica nada, porque só considera schedulings que
  ainda não têm comissão (garantido pelo OneToOneField).
"""
from datetime import date
from decimal import Decimal
from typing import Optional
from uuid import UUID

from django.db import transaction
from django.db.models import QuerySet

from beauty_formula.apps.accounts.selectors.employee_selector import get_employee_by_user_id
from beauty_formula.apps.core.exceptions.payment_exception import (
    CommissionAlreadyExists,
    CommissionCannotBeModified,
    CommissionNotFound,
    SchedulingNotCompleted,
)
from beauty_formula.apps.core.exceptions.permissions import EmployeeNotFoundError
from beauty_formula.apps.core.exceptions.service_exception import SchedulingNotFound
from beauty_formula.apps.payment.models.employee_commission_model import EmployeeCommission
from beauty_formula.apps.payment.repositories.employee_commission_repository import (
    bulk_update_commission_status as bulk_update_commission_status_repo,
    cancel_commission as cancel_commission_repo,
    create_commission as create_commission_repo,
    delete_commission as delete_commission_repo,
    mark_commission_as_paid as mark_commission_as_paid_repo,
    update_commission_value as update_commission_value_repo,
)
from beauty_formula.apps.payment.schemas.employee_commission_schema import (
    CommissionBulkGenerateIn,
    CommissionBulkGenerateOut,
    CommissionBulkStatusIn,
    CommissionBulkStatusOut,
    CommissionCreateIn,
    CommissionOut,
)
from beauty_formula.apps.payment.selectors.employee_commission_selector import (
    count_completed_schedulings_in_period,
    filter_commissions,
    get_commission_by_id,
    get_commission_by_scheduling,
    get_commissions_by_employee,
    get_pending_commission_ids_in_period,
    list_completed_schedulings_without_commission,
)
from beauty_formula.apps.services.models.scheduling import Scheduling
from beauty_formula.apps.services.selectors.scheduling_selector import get_scheduling_by_id


# ═══════════════════════════════════════════════════════════════════════════════
# Helpers internos
# ═══════════════════════════════════════════════════════════════════════════════

def _ensure_pending(commission: EmployeeCommission) -> None:
    if commission.status != EmployeeCommission.CommissionStatus.PENDING:
        raise CommissionCannotBeModified()


def _calculate_commission_value(scheduling: Scheduling) -> Decimal:
    """price_at_booking * service.commission_percentage / 100, sempre a partir do snapshot do agendamento."""
    return (scheduling.price_at_booking * scheduling.service.commission_percentage / Decimal("100")).quantize(Decimal("0.01"))


def _create_commission_for_completed_scheduling(scheduling: Scheduling) -> EmployeeCommission:
    """Assume que `scheduling` já foi validado como COMPLETED e sem comissão."""
    return create_commission_repo(
        employee=scheduling.employee,
        scheduling=scheduling,
        commission_value=_calculate_commission_value(scheduling),
    )


# ═══════════════════════════════════════════════════════════════════════════════
# Admin — criação individual
# ═══════════════════════════════════════════════════════════════════════════════

@transaction.atomic
def create_commission_for_scheduling(data: CommissionCreateIn) -> CommissionOut:
    """Gera a comissão de um único atendimento concluído."""
    scheduling = get_scheduling_by_id(scheduling_id=data.scheduling_id)
    if scheduling is None:
        raise SchedulingNotFound()

    if scheduling.status != Scheduling.SchedulingStatus.COMPLETED:
        raise SchedulingNotCompleted()

    if get_commission_by_scheduling(scheduling_id=scheduling.id) is not None:
        raise CommissionAlreadyExists()

    commission = _create_commission_for_completed_scheduling(scheduling)
    return CommissionOut.from_orm(commission)


# ═══════════════════════════════════════════════════════════════════════════════
# Admin — geração em lote por período
# ═══════════════════════════════════════════════════════════════════════════════

@transaction.atomic
def generate_commissions_for_period(data: CommissionBulkGenerateIn) -> CommissionBulkGenerateOut:
    """
    Gera a comissão de todo atendimento COMPLETED do período que ainda
    não tem comissão. `employee_id=None` cobre todos os funcionários.
    """
    total_completed = count_completed_schedulings_in_period(
        employee_id=data.employee_id, start_date=data.start_date, end_date=data.end_date
    )
    schedulings = list_completed_schedulings_without_commission(
        employee_id=data.employee_id, start_date=data.start_date, end_date=data.end_date
    )

    created = []
    for scheduling in schedulings:
        try:
            commission = _create_commission_for_completed_scheduling(scheduling)
            created.append(CommissionOut.from_orm(commission))
        except CommissionAlreadyExists:
            # Corrida rara: outra geração pegou esse scheduling entre a
            # listagem acima e este create. Só ignora e segue o lote.
            continue

    return CommissionBulkGenerateOut(
        created=created,
        created_count=len(created),
        skipped_count=total_completed - len(created),
        total_completed_schedulings=total_completed,
    )


# ═══════════════════════════════════════════════════════════════════════════════
# Admin — leitura / edição / exclusão individual
# ═══════════════════════════════════════════════════════════════════════════════

def get_commission_detail(commission_id: UUID) -> CommissionOut:
    """Admin vê o detalhe de qualquer comissão."""
    commission = get_commission_by_id(commission_id=commission_id)
    if commission is None:
        raise CommissionNotFound()
    return CommissionOut.from_orm(commission)


def list_all_commissions(
    employee_id: Optional[UUID] = None,
    status: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
) -> QuerySet[EmployeeCommission]:
    """Admin lista todas as comissões, com filtros combináveis."""
    return filter_commissions(employee_id=employee_id, status=status, start_date=start_date, end_date=end_date)


@transaction.atomic
def update_commission_value_by_admin(commission_id: UUID, commission_value: Decimal) -> CommissionOut:
    """Correção manual pontual do valor de uma comissão ainda pendente."""
    commission = get_commission_by_id(commission_id=commission_id)
    if commission is None:
        raise CommissionNotFound()

    _ensure_pending(commission)
    commission = update_commission_value_repo(commission, commission_value=commission_value)
    return CommissionOut.from_orm(commission)


@transaction.atomic
def mark_commission_as_paid_by_admin(commission_id: UUID) -> CommissionOut:
    """Admin confirma o repasse de UMA comissão — marca como paga."""
    commission = get_commission_by_id(commission_id=commission_id)
    if commission is None:
        raise CommissionNotFound()

    _ensure_pending(commission)
    commission = mark_commission_as_paid_repo(commission)
    return CommissionOut.from_orm(commission)


@transaction.atomic
def cancel_commission_by_admin(commission_id: UUID) -> CommissionOut:
    """Admin cancela uma comissão pendente (ex.: atendimento invalidado depois)."""
    commission = get_commission_by_id(commission_id=commission_id)
    if commission is None:
        raise CommissionNotFound()

    _ensure_pending(commission)
    commission = cancel_commission_repo(commission)
    return CommissionOut.from_orm(commission)


@transaction.atomic
def delete_commission_by_admin(commission_id: UUID) -> None:
    """Admin exclui permanentemente um registro de comissão. Use com cautela."""
    commission = get_commission_by_id(commission_id=commission_id)
    if commission is None:
        raise CommissionNotFound()
    delete_commission_repo(commission)


# ═══════════════════════════════════════════════════════════════════════════════
# Admin — atualização de status em lote por período
# ═══════════════════════════════════════════════════════════════════════════════

@transaction.atomic
def update_commission_status_for_period(data: CommissionBulkStatusIn) -> CommissionBulkStatusOut:
    """
    Marca como paga (ou cancela) toda a faixa de comissões PENDING de um
    período — o passo final do fluxo: gerar o período inteiro e, depois
    de conferido, pagar tudo de uma vez.
    """
    commission_ids = get_pending_commission_ids_in_period(
        employee_id=data.employee_id, start_date=data.start_date, end_date=data.end_date
    )
    updated_count = bulk_update_commission_status_repo(commission_ids, status=data.status.value)
    return CommissionBulkStatusOut(updated_count=updated_count, commission_ids=commission_ids)


# ═══════════════════════════════════════════════════════════════════════════════
# Funcionário — somente leitura das próprias comissões
# ═══════════════════════════════════════════════════════════════════════════════

def list_own_commissions_for_employee(
    user_id: UUID,
    status: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
) -> QuerySet[EmployeeCommission]:
    employee = get_employee_by_user_id(user_id=user_id)
    if employee is None:
        raise EmployeeNotFoundError()
    return get_commissions_by_employee(employee_id=employee.id, status=status, start_date=start_date, end_date=end_date)


def get_own_commission_detail_for_employee(user_id: UUID, commission_id: UUID) -> CommissionOut:
    employee = get_employee_by_user_id(user_id=user_id)
    if employee is None:
        raise EmployeeNotFoundError()

    commission = get_commission_by_id(commission_id=commission_id)
    if commission is None or commission.employee_id != employee.id:
        raise CommissionNotFound()

    return CommissionOut.from_orm(commission)