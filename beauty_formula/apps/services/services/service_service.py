import uuid
from datetime import timedelta
from typing import Optional

from ninja import  UploadedFile
from beauty_formula.apps.services.schemas.service_schema import (
    ServiceCreateIn,
    ServiceOut,
)
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