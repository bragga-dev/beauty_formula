import uuid
from datetime import time, datetime, date as date_type, timedelta
from typing import Optional, List

from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils.translation import gettext_lazy as _

from beauty_formula.apps.services.schemas.scheduling_schema import SchedulingOut
from beauty_formula.apps.services.repositories.scheduling_repository import (
    create_scheduling,
    update_scheduling,
    delete_canceled_schedulings_older_than,
    delete_schedulings_by_client,
    delete_schedulings_by_employee,
    delete_schedulings_by_service,
    cancel_scheduling,
    complete_scheduling,
    confirm_scheduling,
    start_scheduling,
    mark_scheduling_as_no_show,
    delete_scheduling,
    reactivate_scheduling,

)


from beauty_formula.apps.core.exceptions.service_exception import (
    ServiceNotFound,
    AssociationNotFound,
    SchedulingConflict,
)
from beauty_formula.apps.core.exceptions.permissions import (
    EmployeeNotFoundError,
    ClientNotFoundError,
    )

from beauty_formula.apps.services.selectors.service_selector import (
    get_service_by_id,
    
)
from beauty_formula.apps.services.selectors.employee_service_selector import (
    get_employee_service,
)
from beauty_formula.apps.services.selectors.availability_selector import (
    is_slot_available,
)

from beauty_formula.apps.accounts.selectors.employee_selector import (
    get_employee_by_id,

)
from beauty_formula.apps.accounts.selectors.client_selector import (
    get_client_by_user_id,

    )

def create_scheduling_service_for_client(
    service_id: uuid.UUID, 
    user_id: uuid.UUID,
    employee_id: uuid.UUID, 
    scheduled_time: datetime,
    notes: Optional[str] = None,
    ) -> SchedulingOut:

    service = get_service_by_id(service_id=service_id)
    if service is None or not service.is_active:
        raise ServiceNotFound()

    client = get_client_by_user_id(user_id=user_id)
    if client is None:
        raise ClientNotFoundError()
    
    employee = get_employee_by_id(employee_id=employee_id)
    if employee is None:
        raise EmployeeNotFoundError()

    employee_service = get_employee_service(employee_id=employee_id, service_id=service_id)
    if employee_service is None or not employee_service.is_active:
        raise AssociationNotFound(_("Esse funcionário não atende esse serviço."))

    end_time = scheduled_time + service.duration
    if not is_slot_available(employee_id=employee_id, start=scheduled_time, end=end_time):
        raise SchedulingConflict()

    try:
        scheduling = create_scheduling(
            service=service,
            client=client,
            employee=employee,
            scheduled_time=scheduled_time,
            notes=notes,
        )
        return SchedulingOut.from_orm(scheduling)
    except DjangoValidationError:
        # Checagem acima teve TOCTOU (outro agendamento entrou entre o
        # is_slot_available e o save()) — o full_clean() do model pegou
        # a sobreposição na hora do save. Traduz pra exceção de domínio
        # em vez de deixar o ValidationError do Django vazar pra api.py.
        raise SchedulingConflict()