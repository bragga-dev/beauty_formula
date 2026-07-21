from beauty_formula.apps.accounts.selectors.user_selector import (
    get_active_users,
    get_active_users_by_role,
    get_all_users,
    get_users_by_date_range,
    get_inactive_users,
    get_users_ordered_by_date,
    get_users_excluding_role,
    get_staff_users,
    get_trusty_users,
    get_user_by_email,
    get_user_by_id,
    get_users_by_role,
    get_users_excluding_id,
    get_user_confirmed_by_role,
    get_user_with_related,
    search_users_by_role_and_status,
    search_users,

)

from beauty_formula.apps.accounts.selectors.client_selector import (
    get_client_by_id,
    get_client_by_instagram,
    get_client_by_phone,
    get_client_by_username,
    get_client_or_404,
    get_clients_by_birth_date_range,
    get_clients_by_birth_date,
    get_clients_by_first_name,
    get_clients_by_gender,
    get_clients_by_email_partial,   
    get_clients_by_name_and_username,
    get_clients_by_phone_partial,
    get_clients_by_ids,
    get_clients_by_last_name,
    get_client_full_name_display,
    get_client_contact_info,
    get_clients_without_phone,
    normalize_phone_for_search,
    get_client_by_user_id,
    get_clients_by_username_partial,
    get_clients_with_birthday_today,
    get_clients_without_instagram,
    get_clients_with_birthday_in_month,
    get_gender_statistics,
    get_clients_by_full_name,
    get_client_by_email,
    get_object_or_404,
    search_clients,
    filter_clients,


)

from beauty_formula.apps.accounts.selectors.employee_selector import (
    get_employee_by_username,
    get_employee_by_email,
    get_employee_by_id,
    get_employee_by_instagram,
    get_employee_by_phone,
    get_employee_by_user_id,
    get_employee_contact_info,
    get_employee_full_name_display,
    get_employee_or_404,
    get_employees_by_bio_keyword,
    get_employees_by_birth_date,
    get_employees_by_birth_date_range,
    get_employees_by_email_partial, 
    get_employees_by_first_name,
    get_employees_by_full_name,
    get_employees_by_gender,
    get_employees_by_ids,
    get_employees_by_last_name,
    get_employees_by_name_and_username,
    get_employees_by_phone_partial,
    get_employees_by_service,
    get_employees_by_services,
    get_employees_by_username_partial,
    get_employees_with_birthday_in_month,
    get_employees_with_birthday_today,
    get_employees_with_services,
    get_employees_without_bio,
    get_employees_without_instagram,
    get_employees_without_phone,
    get_employees_without_services,
    get_object_or_404,
    search_employees,
    filter_employees,
    
)
















__all__ = [
    
    # User
    "get_active_users",
    "get_active_users_by_role",
    "get_all_users",
    "get_users_by_date_range",
    "get_inactive_users",
    "get_users_ordered_by_date",
    "get_users_excluding_role",
    "get_staff_users",
    "get_trusty_users",
    "get_user_by_email",
    "get_user_by_id",
    "get_users_by_role",
    "get_users_excluding_id",
    "get_user_confirmed_by_role",
    "get_user_with_related",
    "search_users_by_role_and_status",
    "search_users",


     # Client
    'get_client_by_id',
    'get_client_or_404',
    'get_client_by_user_id',
    'get_client_by_username',
    'get_clients_by_username_partial',
    'get_clients_by_first_name',
    'get_clients_by_last_name',
    'get_clients_by_full_name',
    'get_client_by_email',
    'get_clients_by_email_partial',
    'get_client_by_phone',
    'get_clients_by_phone_partial',
    'normalize_phone_for_search',
    'get_client_by_instagram',
    'get_clients_by_birth_date',
    'get_clients_by_birth_date_range',
    'get_clients_with_birthday_today',
    'get_clients_with_birthday_in_month',
    'get_clients_by_gender',
    'get_gender_statistics',
    'search_clients',
    'get_clients_by_name_and_username',
    'filter_clients',
    'validate_client_exists',
    'get_client_full_name_display',
    'get_client_contact_info',
    'get_clients_by_ids',
    "get_object_or_404",    
    'get_clients_without_phone',
    'get_clients_without_instagram',


    # Employee
    'get_employee_by_id',
    'get_employee_or_404',
    'get_employee_by_user_id',
    'get_employee_by_username',
    'get_employees_by_username_partial',
    'get_employees_by_first_name',
    'get_employees_by_last_name',
    'get_employees_by_full_name',
    'get_employee_by_email',
    'get_employees_by_email_partial',
    'get_employee_by_phone',
    'get_employees_by_phone_partial',
    'get_employee_by_instagram',
    'get_employees_by_birth_date',
    'get_employees_by_birth_date_range',
    'get_employees_with_birthday_today',
    'get_employees_with_birthday_in_month',
    'get_employees_by_gender',
    'get_employees_by_service',
    'get_employees_by_services',
    'get_employees_with_services',
    'get_employees_without_services',
    'get_employees_by_bio_keyword',
    'search_employees',
    'get_employees_by_name_and_username',
    'filter_employees',
    'validate_employee_exists',
    'get_employee_full_name_display',
    'get_employee_contact_info',
    'get_employees_by_ids',
    'get_employees_without_phone',
    'get_employees_without_instagram',
    'get_employees_without_bio',


]