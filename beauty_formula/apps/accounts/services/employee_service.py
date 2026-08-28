from ninja import UploadedFile
from django.core.exceptions import ValidationError as DjangoValidationError
from beauty_formula.apps.core.validators.image_validator import validate_image_file
from beauty_formula.apps.accounts.selectors.employee_selector import (
  get_employee_by_id,
  get_employee_by_user_id,
)
from beauty_formula.apps.accounts.repositories.employee_repository import (
    set_employee_photo,
    remove_employee_photo,
    update_employee,
)
from beauty_formula.apps.accounts.schemas.employee_schema import EmployeeBookingWindowOut, EmployeeOut, EmployeeUpdateIn
from beauty_formula.apps.accounts.selectors.user_selector import get_user_with_related
from beauty_formula.apps.core.exceptions.user import UserNotFound
from beauty_formula.apps.core.exceptions.permissions import EmployeeNotFoundError, PermissionDenied
from beauty_formula.apps.accounts.models.user import User
from beauty_formula.apps.core.exceptions.media import InvalidImageFile
from uuid import UUID

def upload_employee_profile_photo(user: User, photo: UploadedFile) -> EmployeeOut:
    """
    Faz upload/substituição da foto do Funcionário logado.
    """
    if user.role != User.UserRole.EMPLOYEE:
        raise PermissionDenied("Apenas funcionários podem atualizar esta foto.")

    employee = get_employee_by_user_id(user.id)
    if not employee:
        raise UserNotFound("Funcionário não encontrado.")

    try:
        validate_image_file(photo)
    except DjangoValidationError as e:
        raise InvalidImageFile(e.messages[0] if getattr(e, "messages", None) else str(e))

    updated_employee = set_employee_photo(employee=employee, photo=photo)
    return EmployeeOut.from_orm(updated_employee)


def delete_employee_profile_photo(user: User) -> EmployeeOut:
    """
    Remove a foto do Funcionário logado, voltando para a foto padrão.
    """
    if user.role != User.UserRole.EMPLOYEE:
        raise PermissionDenied("Apenas funcionários podem remover esta foto.")

    employee = get_employee_by_user_id(user.id)
    if not employee:
        raise UserNotFound("Funcionário não encontrado.")

    updated_employee = remove_employee_photo(employee=employee)
    return EmployeeOut.from_orm(updated_employee)


def update_employee_booking_window(employee_id, booking_window_days: int) -> EmployeeBookingWindowOut:
    """
    Admin ajusta a janela de agendamento de UM funcionário — quantos dias
    à frente a agenda dele fica aberta pra clientes agendarem. É uma
    configuração de negócio decidida pelo admin, não pelo próprio
    funcionário — por isso não faz parte de `EmployeeUpdateIn`
    (self-service) e vive num endpoint admin-only à parte.
    """
    employee = get_employee_by_id(employee_id=employee_id)
    if employee is None:
        raise EmployeeNotFoundError()

    updated_employee = update_employee(employee=employee, booking_window_days=booking_window_days)
    return EmployeeBookingWindowOut(employee_id=updated_employee.id, booking_window_days=updated_employee.booking_window_days)



def update_photo_employee_for_admin(employee_id: UUID, photo: UploadedFile) -> EmployeeOut:
    """
    Admin substitui a foto de um funcionário pelo `employee_id` (Employee.pk)
    — mesma chave usada em todas as outras rotas admin de funcionário
    (`/employees/team/{employee_id}/...`), evitando obrigar o front a
    carregar o `user_id` só pra essa ação.
    """
    employee = get_employee_by_id(employee_id=employee_id)
    if employee is None:
        raise EmployeeNotFoundError()

    try:
        validate_image_file(photo)
    except DjangoValidationError as e:
        raise InvalidImageFile(e.messages[0] if getattr(e, "messages", None) else str(e))

    updated_employee = set_employee_photo(employee=employee, photo=photo)
    return EmployeeOut.from_orm(updated_employee)


def update_employee_profile_for_admin(employee_id: UUID, payload: EmployeeUpdateIn) -> EmployeeOut:
    """Admin atualiza os dados de um funcionário pelo `employee_id` (Employee.pk)."""
    employee = get_employee_by_id(employee_id=employee_id)
    if employee is None:
        raise EmployeeNotFoundError()

    fields = payload.dict(exclude_unset=True)
    updated_employee = update_employee(employee=employee, **fields)
    return EmployeeOut.from_orm(updated_employee)