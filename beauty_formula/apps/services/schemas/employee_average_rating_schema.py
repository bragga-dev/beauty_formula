from __future__ import annotations
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional

from ninja import Schema

from beauty_formula.apps.services.models.employee_average_rating import EmployeeAverageRating


class EmployeeAverageRatingOut(Schema):
    """Média de avaliações de um funcionário. Somente leitura."""
    employee_id: uuid.UUID
    average_rating: Decimal = Decimal("0.0")
    total_reviews: int = 0
    updated_at: Optional[datetime] = None

    @classmethod
    def from_orm(cls, average: EmployeeAverageRating) -> "EmployeeAverageRatingOut":
        return cls(
            employee_id=average.employee_id,
            average_rating=average.average_rating,
            total_reviews=average.total_reviews,
            updated_at=average.updated_at,
        )