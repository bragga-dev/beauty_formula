"""
Repositories do módulo de serviços — funções de persistência para
Service, EmployeeService, EmployeeTimeOff e EmployeeWorkingHours.
"""
from beauty_formula.apps.services.repositories.service_repository import (
    activate_service,
    create_service,
    deactivate_service,
    delete_service,
    remove_service_image,
    set_service_image,
    update_service,
)

from beauty_formula.apps.services.repositories.employee_service_repository import (
    activate_employee_service,
    create_employee_service,
    deactivate_employee_service,
    delete_employee_service,
)

from beauty_formula.apps.services.repositories.employee_time_off_repository import (
    create_time_off,
    delete_recurring_time_off_by_employee,
    delete_time_off,
    delete_time_off_by_block_type,
    delete_time_off_by_employee,
    delete_punctual_time_off_by_employee,
    update_time_off,
)

from beauty_formula.apps.services.repositories.employee_working_hours_repository import (
    create_employee_working_hours,
    delete_employee_working_hours,
    update_employee_working_hours,
)


__all__ = [
    # Service
    "activate_service",
    "create_service",
    "deactivate_service",
    "delete_service",
    "remove_service_image",
    "set_service_image",
    "update_service",
    
    # EmployeeService
    "activate_employee_service",
    "create_employee_service",
    "deactivate_employee_service",
    "delete_employee_service",
    
    # EmployeeTimeOff
    "create_time_off",
    "delete_recurring_time_off_by_employee",
    "delete_time_off",
    "delete_time_off_by_block_type",
    "delete_time_off_by_employee",
    "delete_punctual_time_off_by_employee",
    "update_time_off",
    
    # EmployeeWorkingHours
    "create_employee_working_hours",
    "delete_employee_working_hours",
    "update_employee_working_hours",
]