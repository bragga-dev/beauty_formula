"""
Queries de Gerente.
"""
from typing import Optional
from uuid import UUID
from django.db.models import QuerySet

from beauty_formula.apps.accounts.models.manager import Manager


def get_manager_by_id(manager_id: UUID) -> Optional[Manager]:
    return Manager.objects.select_related("user").filter(id=manager_id).first()


def get_manager_by_user_id(user_id: UUID) -> Optional[Manager]:
    return Manager.objects.select_related("user").filter(user_id=user_id).first()


def get_managers() -> QuerySet[Manager]:
    return Manager.objects.select_related("user").all()