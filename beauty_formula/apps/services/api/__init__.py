"""
API do módulo de serviços — endpoints para Service, EmployeeService,
EmployeeWorkingHours, EmployeeTimeOff e Availability.
"""
from beauty_formula.apps.services.api.service import (
    activate_service_router,
    create_service_router,
    deactivate_service_router,
    delete_service_router,
    detail_service_router,
    list_private_services_router,
    list_services_router,
    update_image_service_router,
    update_service_router,
)

from beauty_formula.apps.services.api.employee_service import (
    activate_employee_service_router,
    create_employee_service_router,
    deactivate_employee_service_router,
    delete_employee_service_router,
    list_my_employee_services_router,
)

from beauty_formula.apps.services.api.employee_working_hours import (
    create_working_hours_router,
    delete_working_hours_router,
    list_my_working_hours_router,
    update_working_hours_router,
)

from beauty_formula.apps.services.api.employee_time_off import (
    create_recurring_time_off_router,
    create_punctual_time_off_router,
    delete_all_time_off_router,
    delete_punctual_time_off_router,
    delete_recurring_time_off_router,
    delete_time_off_by_block_type_router,
    delete_time_off_router,
    list_my_active_time_off_router,
    list_my_punctual_time_off_router,
    list_my_recurring_time_off_router,
    list_my_time_off_by_block_type_router,
    list_my_time_off_date_range_router,
    list_my_time_off_on_date_router,
    list_my_time_off_router,
    list_my_upcoming_time_off_router,
    update_punctual_time_off_router,
    update_recurring_time_off_for_employee,
)

from beauty_formula.apps.services.api.scheduling import (
    cancel_employee_scheduling_router,
    cancel_my_scheduling_router,
    cancel_scheduling_router,
    complete_scheduling_router,
    create_scheduling_router,
    delete_scheduling_router,
    get_employee_scheduling_router,
    get_my_scheduling_router,
    get_scheduling_router,
    list_all_schedulings_router,
    list_employee_schedulings_router,
    list_my_schedulings_router,
    mark_no_show_router,
    update_my_scheduling_router,
    update_scheduling_router,
)

from beauty_formula.apps.services.api.availability import (
    employee_availability_router,
)

from beauty_formula.apps.services.api.average_rating import (
    create_average_rating_router,
    list_my_average_ratings_router,
    get_my_average_rating_router,
    update_my_average_rating_router,
    delete_my_average_rating_router,
    list_service_ratings_router,
    get_service_rating_summary_router,
    list_employee_ratings_router,
    get_employee_rating_summary_router,
    list_all_average_ratings_router,
    get_average_rating_detail_router,
    authorize_average_rating_router,
    revoke_average_rating_router,
    delete_average_rating_router,
)


__all__ = [
    # Service
    "activate_service_router",
    "create_service_router",
    "deactivate_service_router",
    "delete_service_router",
    "detail_service_router",
    "list_private_services_router",
    "list_services_router",
    "update_image_service_router",
    "update_service_router",
    
    # EmployeeService
    "activate_employee_service_router",
    "create_employee_service_router",
    "deactivate_employee_service_router",
    "delete_employee_service_router",
    "list_my_employee_services_router",
    
    # EmployeeWorkingHours
    "create_working_hours_router",
    "delete_working_hours_router",
    "list_my_working_hours_router",
    "update_working_hours_router",
    
    # EmployeeTimeOff
    "create_recurring_time_off_router",
    "create_punctual_time_off_router",
    "delete_all_time_off_router",
    "delete_punctual_time_off_router",
    "delete_recurring_time_off_router",
    "delete_time_off_by_block_type_router",
    "delete_time_off_router",
    "list_my_active_time_off_router",
    "list_my_punctual_time_off_router",
    "list_my_recurring_time_off_router",
    "list_my_time_off_by_block_type_router",
    "list_my_time_off_date_range_router",
    "list_my_time_off_on_date_router",
    "list_my_time_off_router",
    "list_my_upcoming_time_off_router",
    "update_punctual_time_off_router",
    "update_recurring_time_off_for_employee",

    # Scheduling
    "create_scheduling_router",
    "list_my_schedulings_router",
    "get_my_scheduling_router",
    "update_my_scheduling_router",
    "cancel_my_scheduling_router",
    "list_employee_schedulings_router",
    "get_employee_scheduling_router",
    "complete_scheduling_router",
    "mark_no_show_router",
    "cancel_employee_scheduling_router",
    "list_all_schedulings_router",
    "get_scheduling_router",
    "update_scheduling_router",
    "cancel_scheduling_router",
    "delete_scheduling_router",
    
    # Availability
    "employee_availability_router",

    # Average Rating
    "create_average_rating_router",
    "list_my_average_ratings_router",
    "get_my_average_rating_router",
    "update_my_average_rating_router",
    "delete_my_average_rating_router",
    "list_service_ratings_router",
    "get_service_rating_summary_router",
    "list_employee_ratings_router",
    "get_employee_rating_summary_router",
    "list_all_average_ratings_router",
    "get_average_rating_detail_router",
    "authorize_average_rating_router",
    "revoke_average_rating_router",
    "delete_average_rating_router",
]