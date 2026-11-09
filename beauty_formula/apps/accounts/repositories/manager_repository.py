"""
Manager Repository — persistência de perfil Gerente.
"""
from typing import Optional
from django.core.files import File
from django.core.files.uploadedfile import InMemoryUploadedFile

from beauty_formula.apps.accounts.models.manager import DEFAULT_MANAGER_PHOTO, Manager
from beauty_formula.apps.accounts.models.user import User


def create_manager(
    user: User,
    first_name: Optional[str] = None,
    last_name: Optional[str] = None,
    photo: Optional[File] = None,
) -> Manager:
    manager = Manager(user=user, first_name=first_name, last_name=last_name, photo=photo)
    manager.save()
    return manager


def update_manager(manager: Manager, **fields) -> Manager:
    for attr, value in fields.items():
        setattr(manager, attr, value)
    manager.full_clean()
    manager.save()
    return manager


def delete_manager(manager: Manager) -> None:
    manager.delete()


def set_manager_photo(manager: Manager, photo: InMemoryUploadedFile) -> Manager:
    manager.photo = photo
    manager.save(update_fields=["photo"])
    return manager


def remove_manager_photo(manager: Manager) -> Manager:
    manager.photo = DEFAULT_MANAGER_PHOTO
    manager.save(update_fields=["photo"])
    return manager