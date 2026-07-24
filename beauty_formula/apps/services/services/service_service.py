import uuid
from django.db.models import QuerySet
from datetime import timedelta
from typing import Optional
from django.core.exceptions import ObjectDoesNotExist
from ninja import  UploadedFile
from beauty_formula.apps.services.schemas.service_schema import (
    ServiceCreateIn,
    ServiceOut,
    ServiceFilter,
    ServiceUpdateIn,

)
from beauty_formula.apps.services.models.service import Service
from beauty_formula.apps.accounts.selectors.user_selector import (
    get_user_by_id,
)
from beauty_formula.apps.accounts.models.user import User
from beauty_formula.apps.core.exceptions.permissions import PermissionDenied
from  beauty_formula.apps.services.repositories.service_repository import(
    create_service,
    update_service,
    deactivate_service,
    delete_service,

)
from beauty_formula.apps.services.selectors.service_selector import (
    get_service_by_id,
    get_active_services,
    
)
from beauty_formula.apps.core.exceptions.service_exception import (
    ServiceNotFound,

)


def create_service_for_admin(user_id: uuid.UUID, data: ServiceCreateIn, image: Optional[UploadedFile] = None) -> ServiceOut:
    user = get_user_by_id(user_id=user_id)
    if not user.role == User.UserRole.ADMIN:
        raise PermissionDenied("Apenas Administradores podem executar essa ação")

    service = create_service(
                   name=data.name,
                   price=data.price,
                   commission_percentage=data.commission_percentage,
                   duration=timedelta(minutes=data.duration_minutes),
                   image=image,
                   description=data.description
    )
    return ServiceOut.from_orm(service)


def update_service_for_admin(user_id: uuid.UUID, service_id: uuid.UUID, payload: ServiceUpdateIn) -> ServiceOut:
    user = get_user_by_id(user_id=user_id)
    if not user.role == User.UserRole.ADMIN:
        raise PermissionDenied("Apenas Administradores podem executar essa ação")

    service = get_service_by_id(service_id=service_id)
    if service is None:
        raise ServiceNotFound()

    fields = payload.model_dump(exclude_unset=True)

    if "duration_minutes" in fields:
        fields["duration"] = timedelta(minutes=fields.pop("duration_minutes"))

    updated = update_service(service=service, **fields)
    return ServiceOut.from_orm(updated)


def list_all_public_services() -> QuerySet[Service]:
    """Lista todos os serviços ativos disponíveis para o público."""
    return get_active_services().order_by("name")



def detail_service(service_id: uuid.UUID) -> ServiceOut:
    service = get_service_by_id(service_id=service_id)
    if service is None:
        raise ServiceNotFound()
    return service


def delete_service_for_admin(user_id: uuid.UUID, service_id:uuid.UUID) -> None:
    user = get_user_by_id(user_id=user_id)
    if not user.role == User.UserRole.ADMIN:
        raise PermissionDenied("Apenas Administradores podem executar essa ação")
    service = get_service_by_id(service_id=service_id)
    if service is None:
        raise ServiceNotFound()
    delete_service(service=service)
    