from uuid import UUID
from beauty_formula.apps.services.models.scheduling import Scheduling
from beauty_formula.apps.accounts.selectors.client_selector import get_client_by_user_id
from beauty_formula.apps.accounts.selectors.employee_selector import  get_employee_by_user_id
from beauty_formula.apps.services.selectors.scheduling_selector import get_scheduling_by_id
from beauty_formula.apps.core.exceptions.permissions import ClientNotFoundError, EmployeeNotFoundError
from beauty_formula.apps.core.exceptions.service_exception import SchedulingNotFound


def get_own_client_scheduling(user_id: UUID, scheduling_id: UUID) -> Scheduling:
    client = get_client_by_user_id(user_id=user_id)
    if client is None:
        raise ClientNotFoundError()

    scheduling = get_scheduling_by_id(scheduling_id=scheduling_id)
    if scheduling is None or scheduling.client_id != client.id:
        raise SchedulingNotFound()

    return scheduling


def get_own_employee_scheduling(user_id: UUID, scheduling_id: UUID) -> Scheduling:
    employee = get_employee_by_user_id(user_id=user_id)
    if employee is None:
        raise EmployeeNotFoundError()

    scheduling = get_scheduling_by_id(scheduling_id=scheduling_id)
    if scheduling is None or scheduling.employee_id != employee.id:
        raise SchedulingNotFound()

    return scheduling
