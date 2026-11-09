"""
Manager Service — CRUD de Gerente.

Cadastro: exclusivo do admin root (a rota garante). Não existe promoção de
cliente/funcionário a gerente: o gerente sempre nasce de um cadastro novo.
"""
from typing import Optional
from uuid import UUID

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.db.models import ProtectedError
from ninja import UploadedFile

from beauty_formula.apps.accounts.models.manager import DEFAULT_MANAGER_PHOTO, Manager
from beauty_formula.apps.accounts.models.user import User
from beauty_formula.apps.accounts.repositories.manager_repository import (
    create_manager,
    delete_manager,
    remove_manager_photo,
    set_manager_photo,
    update_manager,
)
from beauty_formula.apps.accounts.repositories.user_repository import create_user, delete_user
from beauty_formula.apps.accounts.schemas.manager_schema import (
    ManagerCreateIn,
    ManagerOut,
    ManagerUpdateIn,
)
from beauty_formula.apps.accounts.selectors.manager_selector import get_manager_by_id
from beauty_formula.apps.accounts.selectors.user_selector import email_exists
from beauty_formula.apps.accounts.tasks.send_verification_email_manager import (
    send_verification_email_manager,
)
from beauty_formula.apps.core.exceptions.media import InvalidImageFile
from beauty_formula.apps.core.tasks.media import delete_old_media_file
from beauty_formula.apps.core.exceptions.user import (
    AccountHasProtectedRecords,
    UserAlreadyExists,
    UserNotFound,
)
from beauty_formula.apps.core.utils.generate_password import generate_temp_password
from beauty_formula.apps.core.validators.image_validator import validate_image_file


def _replaceable_photo_name(manager: Manager) -> Optional[str]:
    """Nome da foto atual, ou None se for a padrão (que nunca deve ser apagada do storage)."""
    name = manager.photo.name if manager.photo else None
    return None if name == DEFAULT_MANAGER_PHOTO else name


def _discard_old_photo(old_name: Optional[str]) -> None:
    if old_name:
        delete_old_media_file.delay(old_name)


def _get_manager_or_raise(manager_id: UUID):
    manager = get_manager_by_id(manager_id)
    if manager is None:
        raise UserNotFound("Gerente não encontrado.")
    return manager


@transaction.atomic
def register_manager(data: ManagerCreateIn) -> ManagerOut:
    """
    Cria User (role MANAGER) + Manager e envia a senha temporária por e-mail.
    Não retorna tokens: o gerente loga por conta própria com a senha enviada.
    """
    if email_exists(data.email):
        raise UserAlreadyExists("e-mail")

    password = generate_temp_password()
    user = create_user(email=data.email, password=password, role=User.UserRole.MANAGER)
    manager = create_manager(user, first_name=data.first_name, last_name=data.last_name)

    transaction.on_commit(lambda: send_verification_email_manager.delay(user.pk, password))
    return ManagerOut.from_orm(manager)


def get_manager(manager_id: UUID) -> ManagerOut:
    return ManagerOut.from_orm(_get_manager_or_raise(manager_id))


def update_manager_profile(manager_id: UUID, payload: ManagerUpdateIn) -> ManagerOut:
    manager = _get_manager_or_raise(manager_id)
    fields = payload.dict(exclude_unset=True)
    return ManagerOut.from_orm(update_manager(manager, **fields))


def upload_manager_photo(manager_id: UUID, photo: UploadedFile) -> ManagerOut:
    manager = _get_manager_or_raise(manager_id)
    try:
        validate_image_file(photo)
    except DjangoValidationError as e:
        raise InvalidImageFile(e.messages[0] if getattr(e, "messages", None) else str(e))
    old_name = _replaceable_photo_name(manager)
    updated = set_manager_photo(manager, photo)
    _discard_old_photo(old_name)
    return ManagerOut.from_orm(updated)


def delete_manager_photo(manager_id: UUID) -> ManagerOut:
    manager = _get_manager_or_raise(manager_id)
    old_name = _replaceable_photo_name(manager)
    updated = remove_manager_photo(manager)
    _discard_old_photo(old_name)
    return ManagerOut.from_orm(updated)


@transaction.atomic
def remove_manager(manager_id: UUID) -> None:
    """Exclui o gerente e o User dele (o Manager cai em cascata)."""
    manager = _get_manager_or_raise(manager_id)
    user = manager.user
    try:
        delete_manager(manager)
        delete_user(user)
    except ProtectedError:
        raise AccountHasProtectedRecords("Gerente possui registros vinculados e não pode ser excluído.")