from datetime import date as date_type, timedelta
from typing import List
from uuid import UUID

from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from beauty_formula.apps.accounts.models.employee import Employee
from beauty_formula.apps.core.exceptions.service_exception import (
    AssociationNotFound,
    InvalidAvailabilityRequest,
    ServiceNotFound,
)
from beauty_formula.apps.core.utils.time_intervals import Interval
from beauty_formula.apps.services.selectors.availability_selector import (
    get_available_slots,
    has_availability_in_window,
)
from beauty_formula.apps.services.selectors.employee_service_selector import (
    get_employee_service,
    get_employees_for_service,
)
from beauty_formula.apps.services.selectors.service_selector import get_service_by_id

MAX_DAYS_AHEAD = 30


def get_employee_availability(employee_id: UUID, service_id: UUID, target_date: date_type) -> List[Interval]:
    """
    Disponibilidade pública de um funcionário pra um serviço, numa data.

    Regras de negócio (decididas em conversa com o Ed):
    - Sem antecedência mínima — só não deixa ver/agendar num horário que
      já passou (isso o selector já cuida, filtrando pelo `timezone.now()`
      quando a data pedida é hoje).
    - Janela máxima de MAX_DAYS_AHEAD dias no futuro.
    - O funcionário precisa realmente atender esse serviço (EmployeeService
      ativo) — senão a duração usada pra fatiar os slots nem faria sentido.
    """
    service = get_service_by_id(service_id=service_id)
    if service is None:
        raise ServiceNotFound()

    employee_service = get_employee_service(employee_id=employee_id, service_id=service_id)
    if employee_service is None or not employee_service.is_active:
        raise AssociationNotFound(_("Esse funcionário não atende esse serviço."))

    today = timezone.localdate()
    if target_date < today:
        raise InvalidAvailabilityRequest(_("Não é possível consultar disponibilidade no passado."))
    if target_date > today + timedelta(days=MAX_DAYS_AHEAD):
        raise InvalidAvailabilityRequest(
            _("Disponibilidade só pode ser consultada até %(days)s dias no futuro.") % {"days": MAX_DAYS_AHEAD}
        )

    return get_available_slots(employee_id=employee_id, target_date=target_date, slot_duration=service.duration)


def list_eligible_employees_for_service(service_id: UUID) -> List[Employee]:
    """
    Profissionais aptos a atender um serviço E com pelo menos um horário
    livre dentro da janela de agendamento (próximos MAX_DAYS_AHEAD dias).

    Etapa "Profissional" do fluxo de agendamento: estar vinculado ao
    serviço (EmployeeService ativo) não é suficiente — o profissional
    também precisa ter vaga real, senão ele apareceria na lista só pra
    o cliente escolher e não achar nenhum horário na etapa seguinte.
    """
    service = get_service_by_id(service_id=service_id)
    if service is None:
        raise ServiceNotFound()

    today = timezone.localdate()

    eligible: List[Employee] = []
    for employee_service in get_employees_for_service(service_id=service_id, active_only=True):
        employee = employee_service.employee
        if not employee.user.is_active:
            continue
        if has_availability_in_window(employee.id, service.duration, today, MAX_DAYS_AHEAD):
            eligible.append(employee)

    return eligible