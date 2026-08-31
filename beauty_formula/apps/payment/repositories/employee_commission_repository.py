"""
Repository de EmployeeCommission — EXCLUSIVAMENTE persistência (criação,
transições de status e exclusão). Nenhuma consulta/filtro/leitura aqui —
isso é responsabilidade do commission_selector.

Recebe sempre valores/IDs já resolvidos e já validados pelo
commission_service (instância de Employee/Scheduling, lista de IDs já
filtrada por status, etc.) — este módulo só escreve no banco.
"""
from datetime import date
from decimal import Decimal
from uuid import UUID

from django.db import IntegrityError, transaction
from django.utils import timezone

from beauty_formula.apps.accounts.models.employee import Employee
from beauty_formula.apps.accounts.models.user import User
from beauty_formula.apps.core.exceptions.payment_exception import CommissionAlreadyExists
from beauty_formula.apps.payment.models.employee_commission_model import EmployeeCommission
from beauty_formula.apps.services.models.scheduling import Scheduling


@transaction.atomic
def create_commission(
    *,
    employee: Employee,
    scheduling: Scheduling,
    commission_value: Decimal,
    competencia: date,
) -> EmployeeCommission:
    """
    Cria a comissão de um atendimento. O OneToOneField em `scheduling`
    garante no banco que não existe mais de uma comissão pro mesmo
    agendamento — capturamos o IntegrityError do próprio create() e
    traduzimos pra exceção de domínio aqui, igual o
    scheduling_repository faz com ValidationError -> SchedulingConflict.

    `competencia` já vem calculada e resolvida pelo commission_service
    (a partir de scheduling.completed_at, com scheduled_time como
    fallback) — aqui só grava, e também como `competencia_original`
    (snapshot imutável de auditoria, igual ao valor efetivo no momento
    da criação).
    """
    try:
        return EmployeeCommission.objects.create(
            employee=employee,
            scheduling=scheduling,
            commission_value=commission_value,
            competencia=competencia,
            competencia_original=competencia,
        )
    except IntegrityError as e:
        raise CommissionAlreadyExists() from e


@transaction.atomic
def update_commission_competencia(
    commission: EmployeeCommission, *, competencia: date, changed_by: User
) -> EmployeeCommission:
    """
    Correção manual da competência (mês de referência) por um admin —
    não mexe em `competencia_original`, que continua sendo o valor
    calculado automaticamente no momento da criação, pra sempre dar pra
    ver se e quanto o admin desviou do valor "natural".
    """
    commission.competencia = competencia
    commission.competencia_changed_by = changed_by
    commission.competencia_changed_at = timezone.now()
    commission.save(
        update_fields=["competencia", "competencia_changed_by", "competencia_changed_at", "updated_at"]
    )
    return commission


@transaction.atomic
def update_commission_value(commission: EmployeeCommission, *, commission_value: Decimal) -> EmployeeCommission:
    """Ajuste manual pontual do valor de uma comissão ainda PENDING (checagem de status é do service)."""
    commission.commission_value = commission_value
    commission.save(update_fields=["commission_value", "updated_at"])
    return commission


@transaction.atomic
def mark_commission_as_paid(commission: EmployeeCommission, *, paid_by: User | None = None) -> EmployeeCommission:
    """Marca a comissão como paga, registrando o momento do repasse e, se informado, o admin responsável."""
    commission.status = EmployeeCommission.CommissionStatus.PAID
    commission.paid_at = timezone.now()
    fields = ["status", "paid_at", "updated_at"]
    if paid_by is not None:
        commission.paid_by = paid_by
        fields.append("paid_by")
    commission.save(update_fields=fields)
    return commission


@transaction.atomic
def cancel_commission(commission: EmployeeCommission) -> EmployeeCommission:
    """Cancela uma comissão (não gerou/não vai gerar repasse)."""
    commission.status = EmployeeCommission.CommissionStatus.CANCELED
    commission.save(update_fields=["status", "updated_at"])
    return commission


@transaction.atomic
def revert_commission_to_pending(commission: EmployeeCommission) -> EmployeeCommission:
    """
    Reverte uma comissão PAGA de volta pra PENDING — corrige um pagamento
    marcado por engano, sem apagar o histórico (o registro nunca é
    excluído, só transita de status; `paid_at` é limpo pois deixou de
    valer).
    """
    commission.status = EmployeeCommission.CommissionStatus.PENDING
    commission.paid_at = None
    commission.save(update_fields=["status", "paid_at", "updated_at"])
    return commission


@transaction.atomic
def bulk_update_commission_status(commissions: list[EmployeeCommission], *, status: str) -> int:
    """
    Recebe as instâncias já resolvidas e filtradas pelo selector (ex.: só
    as PENDING de um período) — não faz nenhuma busca, só grava o novo
    status em cada uma via `bulk_update`, sem passar por `save()`/signals.
    """
    if not commissions:
        return 0

    now = timezone.now()
    fields = ["status", "updated_at"]

    for commission in commissions:
        commission.status = status
        commission.updated_at = now
        if status == EmployeeCommission.CommissionStatus.PAID:
            commission.paid_at = now

    if status == EmployeeCommission.CommissionStatus.PAID:
        fields.append("paid_at")

    EmployeeCommission.objects.bulk_update(commissions, fields=fields)
    return len(commissions)