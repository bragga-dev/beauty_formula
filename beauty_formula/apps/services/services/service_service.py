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
    ServiceUpdateStatusIn,

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
    activate_service,
    set_service_image,
    remove_service_image,

)
from beauty_formula.apps.services.selectors.service_selector import (
    get_service_by_id,
    get_active_services,
    get_inactive_services,
    get_service_by_id_inactivate,
    get_all_services,
    
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
    return get_active_services()

def list_all_private_services(user_id: uuid.UUID) -> QuerySet[Service]:
    """Lista todos os serviços ativos e inativos, apenas Admins podem acessar esse recurso"""
    user = get_user_by_id(user_id=user_id)
    if not user.role == User.UserRole.ADMIN:
        raise PermissionDenied("Apenas Administradores podem executar essa ação")    
    return get_all_services()

def detail_service(service_id: uuid.UUID) -> ServiceOut:
    """Exibe detalhes deum serviço"""
    service = get_service_by_id(service_id=service_id)
    if service is None:
        raise ServiceNotFound()
    return service


def delete_service_for_admin(user_id: uuid.UUID, service_id:uuid.UUID) -> None:
    """Deleta serviços, apenas admins podem fazer essa ação"""
    user = get_user_by_id(user_id=user_id)
    if not user.role == User.UserRole.ADMIN:
        raise PermissionDenied("Apenas Administradores podem executar essa ação")
    service = get_service_by_id(service_id=service_id)
    if service is None:
        raise ServiceNotFound()
    delete_service(service=service)


def deactivate_service_for_admin(user_id: uuid.UUID, service_id: uuid.UUID) -> ServiceOut:
    """Desativa um serviço, apenas Admin pode fazer essa ação"""
    user = get_user_by_id(user_id=user_id)
    if not user.role == User.UserRole.ADMIN:
        raise PermissionDenied("Apenas Administradores podem executar essa ação")

    service = get_service_by_id(service_id=service_id)
    if service is None:
        raise ServiceNotFound()

    updated_service = deactivate_service(service=service)
    return ServiceOut.from_orm(updated_service)


def activate_service_for_admin(user_id: uuid.UUID, service_id: uuid.UUID) -> ServiceOut:
    """Ativa Serviço, apenas Admins podem fazer essa ação"""
    user = get_user_by_id(user_id=user_id)
    if not user.role == User.UserRole.ADMIN:
        raise PermissionDenied("Apenas Administradores podem executar essa ação")

    service = get_service_by_id_inactivate(service_id=service_id)
    if service is None:
        raise ServiceNotFound()

    updated_service = activate_service(service=service)
    return ServiceOut.from_orm(updated_service)

def update_image_service_for_admin(user_id: uuid.UUID, service_id: uuid.UUID, image: UploadedFile) -> ServiceOut:
    user = get_user_by_id(user_id=user_id)
    if not user.role == User.UserRole.ADMIN:
        raise PermissionDenied("Apenas Administradores podem executar essa ação")

    service = get_service_by_id(service_id=service_id)
    if service is None:
        raise ServiceNotFound()
    image_upted = set_service_image(service=service, image=image)
    return ServiceOut.from_orm(image_upted)