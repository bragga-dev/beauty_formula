import uuid
from datetime import time
from typing import Optional

from django.db.models import QuerySet

from beauty_formula.apps.accounts.selectors.employee_selector import get_employee_by_user_id
from beauty_formula.apps.core.exceptions.permissions import EmployeeNotFoundError
from beauty_formula.apps.core.exceptions.service_exception import WorkingHoursNotFound
from beauty_formula.apps.services.models.employee_works_hours import EmployeeWorkingHours
from beauty_formula.apps.services.repositories.employee_working_hours_repository import (
    create_employee_working_hours,
    delete_employee_working_hours,
    update_employee_working_hours,
)
from beauty_formula.apps.services.selectors.employee_working_hours_selector import (
    get_all_working_hours_for_employee,
    get_working_hours_by_id,
)


def _get_own_working_hours(user_id: uuid.UUID, working_hours_id: uuid.UUID) -> EmployeeWorkingHours:
    """
    Resolve o Employee dono e garante que o turno pertence a ele — mesmo
    padrão do `_get_own_employee_service` já usado em EmployeeService.
    """
    employee = get_employee_by_user_id(user_id=user_id)
    if employee is None:
        raise EmployeeNotFoundError()

    working_hours = get_working_hours_by_id(working_hours_id=working_hours_id)
    if working_hours is None or working_hours.employee_id != employee.id:
        raise WorkingHoursNotFound()

    return working_hours


def list_own_working_hours(user_id: uuid.UUID) -> QuerySet[EmployeeWorkingHours]:
    """Lista a semana inteira de turnos do próprio funcionário."""
    employee = get_employee_by_user_id(user_id=user_id)
    if employee is None:
        raise EmployeeNotFoundError()

    return get_all_working_hours_for_employee(employee_id=employee.id)


def create_working_hours_for_employee(user_id: uuid.UUID, weekday: int, start_time: time, end_time: time) -> EmployeeWorkingHours:
    """
    Cadastra um turno pro próprio funcionário. A validação de negócio
    (overlap com outro turno do mesmo dia, start_time < end_time)
    acontece no model via `clean()`/`save()` — aqui só resolve o
    Employee e delega pro repository.
    """
    employee = get_employee_by_user_id(user_id=user_id)
    if employee is None:
        raise EmployeeNotFoundError()

    return create_employee_working_hours(employee=employee, weekday=weekday, start_time=start_time, end_time=end_time)


def update_working_hours_for_employee(
    user_id: uuid.UUID,
    working_hours_id: uuid.UUID,
    weekday: Optional[int] = None,
    start_time: Optional[time] = None,
    end_time: Optional[time] = None,
) -> EmployeeWorkingHours:
    """Atualiza parcialmente um turno próprio (checa posse antes)."""
    working_hours = _get_own_working_hours(user_id, working_hours_id)
    return update_employee_working_hours(working_hours, weekday=weekday, start_time=start_time, end_time=end_time)


def delete_working_hours_for_employee(user_id: uuid.UUID, working_hours_id: uuid.UUID) -> None:
    """Exclui permanentemente um turno próprio (checa posse antes)."""
    working_hours = _get_own_working_hours(user_id, working_hours_id)
    delete_employee_working_hours(working_hours)