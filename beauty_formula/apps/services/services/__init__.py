"""
Camada de Serviços do módulo de serviços — orquestra as regras de negócio
para Service, EmployeeService, EmployeeTimeOff, EmployeeWorkingHours
e Availability.
"""
from beauty_formula.apps.services.services.service_service import (
    activate_service_for_admin,
    create_service_for_admin,
    deactivate_service_for_admin,
    delete_service_for_admin,
    detail_service,
    list_all_private_services,
    list_all_public_services,
    update_image_service_for_admin,
    update_service_for_admin,
)

from beauty_formula.apps.services.services.employee_service_service import (
    activate_employee_service_for_employee,
    create_employee_service_for_employee,
    deactivate_employee_service_for_employee,
    delete_employee_service_for_employee,
    list_own_employee_services,
)

from beauty_formula.apps.services.services.employee_working_hours_service import (
    create_working_hours_for_employee,
    delete_working_hours_for_employee,
    list_own_working_hours,
    update_working_hours_for_employee,
)

from beauty_formula.apps.services.services.availability_service import (
    get_employee_availability,
)

from beauty_formula.apps.services.services.employee_time_off_service import (

    create_recurring_time_off_for_employee,
    create_punctual_time_off_for_employee,
    update_recurring_time_off_for_employee,
    update_punctual_time_off_for_employee,
    delete_time_off_for_employee,
    delete_all_time_off_for_employee,
    delete_recurring_time_off_for_employee,
    delete_punctual_time_off_for_employee,
    delete_time_off_by_block_type_for_employee,
    list_own_time_off,
    list_own_recurring_time_off,
    list_own_punctual_time_off,
    list_own_time_off_by_block_type,
    list_own_time_off_on_date,
    list_own_time_off_date_range,
    list_own_active_time_off,
    list_own_upcoming_time_off,

)


__all__ = [
    # Service
    "activate_service_for_admin",
    "create_service_for_admin",
    "deactivate_service_for_admin",
    "delete_service_for_admin",
    "detail_service",
    "list_all_private_services",
    "list_all_public_services",
    "update_image_service_for_admin",
    "update_service_for_admin",
    
    # EmployeeService
    "activate_employee_service_for_employee",
    "create_employee_service_for_employee",
    "deactivate_employee_service_for_employee",
    "delete_employee_service_for_employee",
    "list_own_employee_services",
    
    # EmployeeWorkingHours
    "create_working_hours_for_employee",
    "delete_working_hours_for_employee",
    "list_own_working_hours",
    "update_working_hours_for_employee",
    
    # Availability
    "get_employee_availability",

    # Employee Time Off
    "create_recurring_time_off_for_employee",
    "create_punctual_time_off_for_employee",
    "update_recurring_time_off_for_employee",
    "update_punctual_time_off_for_employee",
    "delete_time_off_for_employee",
    "delete_all_time_off_for_employee",
    "delete_recurring_time_off_for_employee",
    "delete_punctual_time_off_for_employee",
    "delete_time_off_by_block_type_for_employee",
    "list_own_time_off",
    "list_own_recurring_time_off",
    "list_own_punctual_time_off",
    "list_own_time_off_by_block_type",
    "list_own_time_off_on_date",
    "list_own_time_off_date_range",
    "list_own_active_time_off",
    "list_own_upcoming_time_off",

]