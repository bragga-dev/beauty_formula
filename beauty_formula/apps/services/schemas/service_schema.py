import uuid
from decimal import Decimal
from typing import Optional
from ninja import Schema

from beauty_formula.apps.services.models.service import Service


class ServiceOut(Schema):
    """
    Representação pública de um serviço. Deliberadamente NÃO inclui
    `commission_percentage` nem `total_bookings` — são dado interno de
    negócio, não deveriam ser expostos numa página pública.
    """
    id: uuid.UUID
    name: str
    description: Optional[str] = None
    price: Decimal
    duration_minutes: Optional[int] = None
    image_url: str

    @classmethod
    def from_orm(cls, service: Service) -> "ServiceOut":
        return cls(
            id=service.id,
            name=service.name,
            description=service.description,
            price=service.price,
            duration_minutes=int(service.duration.total_seconds() // 60) if service.duration else None,
            image_url=service.image_url,
        )


__all__ = ["ServiceOut"]