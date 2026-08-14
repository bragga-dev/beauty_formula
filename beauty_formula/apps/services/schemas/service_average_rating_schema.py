from __future__ import annotations
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional

from ninja import Schema

from beauty_formula.apps.services.models.service_average_rating import ServiceAverageRating


class ServiceAverageRatingOut(Schema):
    """Média de avaliações de um serviço. Somente leitura."""
    service_id: uuid.UUID
    average_rating: Decimal = Decimal("0.0")
    total_reviews: int = 0
    updated_at: Optional[datetime] = None

    @classmethod
    def from_orm(cls, average: ServiceAverageRating) -> "ServiceAverageRatingOut":
        return cls(
            service_id=average.service_id,
            average_rating=average.average_rating,
            total_reviews=average.total_reviews,
            updated_at=average.updated_at,
        )