



from ninja import UploadedFile
from django.core.exceptions import ValidationError as DjangoValidationError
from beauty_formula.apps.core.validators.image_validator import validate_image_file
from beauty_formula.apps.accounts.selectors.employee_selector import (
  get_employee_by_user_id,
)
from beauty_formula.apps.accounts.repositories.employee_repository import set_employee_photo, remove_employee_photo
from beauty_formula.apps.accounts.schemas.employee_schema import EmployeeOut
from beauty_formula.apps.accounts.selectors.user_selector import get_user_with_related
from beauty_formula.apps.core.exceptions.user import UserNotFound
from beauty_formula.apps.core.exceptions.permissions import PermissionDenied
from beauty_formula.apps.accounts.models.user import User
from beauty_formula.apps.core.exceptions.media import InvalidImageFile


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