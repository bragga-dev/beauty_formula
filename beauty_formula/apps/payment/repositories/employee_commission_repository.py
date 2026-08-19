"""
Repository de EmployeeCommission — EXCLUSIVAMENTE persistência (criação,
transições de status e exclusão). Nenhuma consulta/filtro/leitura aqui —
isso é responsabilidade do commission_selector.

Recebe sempre valores/IDs já resolvidos e já validados pelo
commission_service (instância de Employee/Scheduling, lista de IDs já
filtrada por status, etc.) — este módulo só escreve no banco.
"""
from decimal import Decimal
from uuid import UUID

from django.db import IntegrityError, transaction
from django.utils import timezone

from beauty_formula.apps.accounts.models.employee import Employee
from beauty_formula.apps.core.exceptions.payment_exception import CommissionAlreadyExists
from beauty_formula.apps.payment.models.employee_commission_model import EmployeeCommission
from beauty_formula.apps.services.models.scheduling import Scheduling


@transaction.atomic
def create_commission(
    *,
    employee: Employee,
    scheduling: Scheduling,
    commission_value: Decimal,
) -> EmployeeCommission:
    """
    Cria a comissão de um atendimento. O OneToOneField em `scheduling`
    garante no banco que não existe mais de uma comissão pro mesmo
    agendamento — capturamos o IntegrityError do próprio create() e
    traduzimos pra exceção de domínio aqui, igual o
    scheduling_repository faz com ValidationError -> SchedulingConflict.
    """
    try:
        return EmployeeCommission.objects.create(
            employee=employee,
            scheduling=scheduling,
            commission_value=commission_value,
        )
    except IntegrityError as e:
        raise CommissionAlreadyExists() from e


@transaction.atomic
def update_commission_value(commission: EmployeeCommission, *, commission_value: Decimal) -> EmployeeCommission:
    """Ajuste manual pontual do valor de uma comissão ainda PENDING (checagem de status é do service)."""
    commission.commission_value = commission_value
    commission.save(update_fields=["commission_value", "updated_at"])
    return commission


@transaction.atomic
def mark_commission_as_paid(commission: EmployeeCommission) -> EmployeeCommission:
    """Marca a comissão como paga, registrando o momento do repasse."""
    commission.status = EmployeeCommission.CommissionStatus.PAID
    commission.paid_at = timezone.now()
    commission.save(update_fields=["status", "paid_at", "updated_at"])
    return commission


@transaction.atomic
def cancel_commission(commission: EmployeeCommission) -> EmployeeCommission:
    """Cancela uma comissão (não gerou/não vai gerar repasse)."""
    commission.status = EmployeeCommission.CommissionStatus.CANCELED
    commission.save(update_fields=["status", "updated_at"])
    return commission


@transaction.atomic
def delete_commission(commission: EmployeeCommission) -> None:
    commission.delete()


@transaction.atomic
def bulk_update_commission_status(commission_ids: list[UUID], *, status: str) -> int:
    """
    Persiste o novo status pra um conjunto de IDs já resolvido e já
    filtrado pelo service/selector (ex.: só os PENDING de um período).
    Não decide QUAIS ids são elegíveis — só grava. `update()` em massa
    não passa por `save()`/signals, mas o model não depende de nenhum,
    então é seguro e bem mais rápido que um loop.
    """
    update_fields = {"status": status, "updated_at": timezone.now()}
    if status == EmployeeCommission.CommissionStatus.PAID:
        update_fields["paid_at"] = timezone.now()

    return EmployeeCommission.objects.filter(id__in=commission_ids).update(**update_fields)