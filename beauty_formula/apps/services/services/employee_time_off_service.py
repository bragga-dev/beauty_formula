"""
Serviço de EmployeeTimeOff — orquestra as regras de negócio para
bloqueios de horário (recorrentes ou pontuais) de um funcionário.
"""
import uuid
from datetime import time, datetime, date as date_type, timedelta
from typing import Optional, List

from django.db.models import QuerySet
from django.utils import timezone

from beauty_formula.apps.accounts.selectors.employee_selector import get_employee_by_user_id
from beauty_formula.apps.core.exceptions.permissions import EmployeeNotFoundError
from beauty_formula.apps.core.exceptions.service_exception import (
    TimeOffNotFound,
    TimeOffConflict,
    InvalidTimeOffRequest,
)
from beauty_formula.apps.services.models.employee_time_off import EmployeeTimeOff
from beauty_formula.apps.services.tasks.expire_punctual_time_off import expire_punctual_time_off
from beauty_formula.apps.services.repositories.employee_time_off_repository import (
    create_time_off,
    update_time_off,
    delete_time_off,
    delete_time_off_by_employee,
    delete_recurring_time_off_by_employee,
    delete_punctual_time_off_by_employee,
    delete_time_off_by_block_type,
)
from beauty_formula.apps.services.selectors.employee_time_off_selector import (
    get_time_off_by_id,
    get_time_off_for_employee,
    get_recurring_time_off_for_employee,
    get_punctual_time_off_for_employee,
    get_time_off_by_block_type,
    get_time_off_for_employee_on_date,
    get_time_off_for_employee_date_range,
    get_active_time_off_for_employee,
    get_upcoming_time_off_for_employee,
    get_time_off_conflicts,
    has_time_off_conflict,
    validate_time_off_belongs_to_employee,
)


def _schedule_expiration(time_off: EmployeeTimeOff) -> None:
    """
    Agenda (ou reagenda) a expiração automática de um bloqueio pontual.

    Chamado depois de toda criação/atualização bem-sucedida — se o
    registro resultante não é (ou não é mais) pontual, não agenda nada.
    Cada chamada agenda uma task NOVA pro end_datetime atual; tasks
    antigas de agendamentos anteriores (de antes de uma edição) viram
    no-op sozinhas — ver expire_punctual_time_off em services/tasks.py.
    """
    if not time_off.is_punctual:
        return

    expire_punctual_time_off.apply_async(
        args=[str(time_off.id)],
        eta=time_off.end_datetime + timedelta(minutes=1),
    )


def _get_own_time_off(user_id: uuid.UUID, time_off_id: uuid.UUID) -> EmployeeTimeOff:
    """
    Resolve o Employee dono e garante que o bloqueio pertence a ele —
    mesmo padrão do `_get_own_employee_service` já usado em outros serviços.
    """
    employee = get_employee_by_user_id(user_id=user_id)
    if employee is None:
        raise EmployeeNotFoundError()

    time_off = get_time_off_by_id(time_off_id=time_off_id)
    if time_off is None or time_off.employee_id != employee.id:
        raise TimeOffNotFound()

    return time_off


def list_own_time_off(user_id: uuid.UUID) -> QuerySet[EmployeeTimeOff]:
    """
    Lista todos os bloqueios do próprio funcionário.
    """
    employee = get_employee_by_user_id(user_id=user_id)
    if employee is None:
        raise EmployeeNotFoundError()

    return get_time_off_for_employee(employee_id=employee.id)


def list_own_recurring_time_off(user_id: uuid.UUID) -> QuerySet[EmployeeTimeOff]:
    """
    Lista apenas bloqueios recorrentes do próprio funcionário.
    """
    employee = get_employee_by_user_id(user_id=user_id)
    if employee is None:
        raise EmployeeNotFoundError()

    return get_recurring_time_off_for_employee(employee_id=employee.id)


def list_own_punctual_time_off(user_id: uuid.UUID) -> QuerySet[EmployeeTimeOff]:
    """
    Lista apenas bloqueios pontuais do próprio funcionário.
    """
    employee = get_employee_by_user_id(user_id=user_id)
    if employee is None:
        raise EmployeeNotFoundError()

    return get_punctual_time_off_for_employee(employee_id=employee.id)


def list_own_time_off_by_block_type(user_id: uuid.UUID, block_type: str) -> QuerySet[EmployeeTimeOff]:
    """
    Lista bloqueios do próprio funcionário por tipo.
    """
    employee = get_employee_by_user_id(user_id=user_id)
    if employee is None:
        raise EmployeeNotFoundError()

    return get_time_off_by_block_type(employee_id=employee.id, block_type=block_type)


def list_own_time_off_on_date(user_id: uuid.UUID, target_date: date_type) -> QuerySet[EmployeeTimeOff]:
    """
    Lista bloqueios do próprio funcionário para uma data específica.
    """
    employee = get_employee_by_user_id(user_id=user_id)
    if employee is None:
        raise EmployeeNotFoundError()

    weekday = target_date.weekday()
    return get_time_off_for_employee_on_date(
        employee_id=employee.id,
        weekday=weekday,
        target_date=target_date
    )


def list_own_time_off_date_range(
    user_id: uuid.UUID,
    start_date: date_type,
    end_date: date_type
) -> QuerySet[EmployeeTimeOff]:
    """
    Lista bloqueios do próprio funcionário em um período.
    """
    employee = get_employee_by_user_id(user_id=user_id)
    if employee is None:
        raise EmployeeNotFoundError()

    return get_time_off_for_employee_date_range(
        employee_id=employee.id,
        start_date=start_date,
        end_date=end_date
    )


def list_own_active_time_off(user_id: uuid.UUID) -> QuerySet[EmployeeTimeOff]:
    """
    Lista bloqueios ativos do próprio funcionário (considerando data/hora atual).
    """
    employee = get_employee_by_user_id(user_id=user_id)
    if employee is None:
        raise EmployeeNotFoundError()

    return get_active_time_off_for_employee(employee_id=employee.id)


def list_own_upcoming_time_off(user_id: uuid.UUID, days_ahead: int = 7) -> QuerySet[EmployeeTimeOff]:
    """
    Lista bloqueios futuros do próprio funcionário (próximos N dias).
    """
    employee = get_employee_by_user_id(user_id=user_id)
    if employee is None:
        raise EmployeeNotFoundError()

    return get_upcoming_time_off_for_employee(employee_id=employee.id, days_ahead=days_ahead)


def create_recurring_time_off_for_employee(
    user_id: uuid.UUID,
    block_type: str,
    weekday: int,
    start_time: time,
    end_time: time,
) -> EmployeeTimeOff:
    """
    Cria um bloqueio RECORRENTE (ex: almoço toda terça, 12h-13h) pro
    próprio funcionário. block_modality=RECURRING é fixado aqui — quem
    chama essa função não escolhe a modalidade, o endpoint que a chama
    (POST /employee-time-off/recurring/) já é exclusivo pra isso.
    """
    employee = get_employee_by_user_id(user_id=user_id)
    if employee is None:
        raise EmployeeNotFoundError()

    return create_time_off(
        employee=employee,
        block_type=block_type,
        block_modality=EmployeeTimeOff.BlockModality.RECURRING,
        weekday=weekday,
        start_time=start_time,
        end_time=end_time,
    )


def create_punctual_time_off_for_employee(
    user_id: uuid.UUID,
    block_type: str,
    start_datetime: datetime,
    end_datetime: datetime,
) -> EmployeeTimeOff:
    """
    Cria um bloqueio PONTUAL (ex: consulta médica dia X) pro próprio
    funcionário. Agenda a expiração automática (soft delete via Celery)
    logo em seguida — ver _schedule_expiration.
    """
    employee = get_employee_by_user_id(user_id=user_id)
    if employee is None:
        raise EmployeeNotFoundError()

    if has_time_off_conflict(employee_id=employee.id, start_datetime=start_datetime, end_datetime=end_datetime):
        raise TimeOffConflict("Já existe um bloqueio neste período.")

    time_off = create_time_off(
        employee=employee,
        block_type=block_type,
        block_modality=EmployeeTimeOff.BlockModality.PUNCTUAL,
        start_datetime=start_datetime,
        end_datetime=end_datetime,
    )
    _schedule_expiration(time_off)
    return time_off


def update_recurring_time_off_for_employee(
    user_id: uuid.UUID,
    time_off_id: uuid.UUID,
    block_type: Optional[str] = None,
    weekday: Optional[int] = None,
    start_time: Optional[time] = None,
    end_time: Optional[time] = None,
) -> EmployeeTimeOff:
    """
    Atualiza parcialmente um bloqueio RECORRENTE próprio (checa posse
    e modalidade antes). None = mantém o valor atual.

    Não troca a modalidade do registro — só serve pra editar um
    bloqueio que já é recorrente, mesmo espírito de
    create_recurring_time_off_for_employee: quem chama essa função já
    sabe qual modalidade quer, o endpoint que a chama
    (PATCH /employee-time-off/recurring/{id}) já é exclusivo pra isso.
    """
    time_off = _get_own_time_off(user_id, time_off_id)

    if not time_off.is_recurring:
        raise InvalidTimeOffRequest("Este bloqueio não é recorrente.")

    time_off = update_time_off(
        time_off=time_off,
        block_type=block_type,
        weekday=weekday,
        start_time=start_time,
        end_time=end_time,
    )
    return time_off


def update_punctual_time_off_for_employee(
    user_id: uuid.UUID,
    time_off_id: uuid.UUID,
    block_type: Optional[str] = None,
    start_datetime: Optional[datetime] = None,
    end_datetime: Optional[datetime] = None,
) -> EmployeeTimeOff:
    """
    Atualiza parcialmente um bloqueio PONTUAL próprio (checa posse e
    modalidade antes). None = mantém o valor atual. Reagenda a
    expiração automática (soft delete via Celery) se start/end mudou
    — ver _schedule_expiration.

    Não troca a modalidade do registro — só serve pra editar um
    bloqueio que já é pontual.
    """
    time_off = _get_own_time_off(user_id, time_off_id)

    if not time_off.is_punctual:
        raise InvalidTimeOffRequest("Este bloqueio não é pontual.")

    # Verifica conflitos se estiver alterando datas/horários
    new_start_datetime = start_datetime if start_datetime is not None else time_off.start_datetime
    new_end_datetime = end_datetime if end_datetime is not None else time_off.end_datetime

    if new_start_datetime and new_end_datetime:
        # Ignora o próprio bloqueio na verificação de conflito
        conflicts = get_time_off_conflicts(
            employee_id=time_off.employee_id,
            start_datetime=new_start_datetime,
            end_datetime=new_end_datetime
        ).exclude(id=time_off.id)

        if conflicts.exists():
            raise TimeOffConflict("Já existe um bloqueio neste período.")

    time_off = update_time_off(
        time_off=time_off,
        block_type=block_type,
        start_datetime=start_datetime,
        end_datetime=end_datetime,
    )
    _schedule_expiration(time_off)
    return time_off


def delete_time_off_for_employee(user_id: uuid.UUID, time_off_id: uuid.UUID) -> None:
    """
    Exclui permanentemente um bloqueio próprio (checa posse antes).
    """
    time_off = _get_own_time_off(user_id, time_off_id)
    delete_time_off(time_off)


def delete_all_time_off_for_employee(user_id: uuid.UUID) -> None:
    """
    Exclui todos os bloqueios do próprio funcionário.
    """
    employee = get_employee_by_user_id(user_id=user_id)
    if employee is None:
        raise EmployeeNotFoundError()

    delete_time_off_by_employee(employee)


def delete_recurring_time_off_for_employee(user_id: uuid.UUID) -> None:
    """
    Exclui todos os bloqueios recorrentes do próprio funcionário.
    """
    employee = get_employee_by_user_id(user_id=user_id)
    if employee is None:
        raise EmployeeNotFoundError()

    delete_recurring_time_off_by_employee(employee)


def delete_punctual_time_off_for_employee(user_id: uuid.UUID) -> None:
    """
    Exclui todos os bloqueios pontuais do próprio funcionário.
    """
    employee = get_employee_by_user_id(user_id=user_id)
    if employee is None:
        raise EmployeeNotFoundError()

    delete_punctual_time_off_by_employee(employee)


def delete_time_off_by_block_type_for_employee(user_id: uuid.UUID, block_type: str) -> None:
    """
    Exclui todos os bloqueios do próprio funcionário por tipo específico.
    """
    employee = get_employee_by_user_id(user_id=user_id)
    if employee is None:
        raise EmployeeNotFoundError()

    delete_time_off_by_block_type(employee, block_type)