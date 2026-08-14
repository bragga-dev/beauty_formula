from __future__ import annotations
import uuid
from datetime import datetime
from typing import Optional
from enum import Enum

from ninja import Schema
from pydantic import field_validator

from beauty_formula.apps.services.models.average_rating import AverageRating
from beauty_formula.apps.accounts.schemas.client_schema import ClientOut
from beauty_formula.apps.accounts.schemas.employee_schema import EmployeeOut
from beauty_formula.apps.services.schemas.service_schema import ServiceOut


MAX_COMMENT_LENGTH = 500


class RatingEnum(int, Enum):
    ONE_STAR = 1
    TWO_STARS = 2
    THREE_STARS = 3
    FOUR_STARS = 4
    FIVE_STARS = 5

    @classmethod
    def get_display_name(cls, value: int) -> str:
        choices_dict = dict(AverageRating.RatingChoices.choices)
        return choices_dict.get(value, str(value))


def _validate_comment(v: Optional[str]) -> Optional[str]:
    if v is None:
        return v
    v = v.strip()
    if not v:
        return None
    if len(v) > MAX_COMMENT_LENGTH:
        raise ValueError(f"Comentário não pode exceder {MAX_COMMENT_LENGTH} caracteres.")
    return v


class AverageRatingOut(Schema):
    """Avaliação pública — o que qualquer visitante pode ver de uma avaliação autorizada."""
    id: uuid.UUID
    service: ServiceOut
    employee: EmployeeOut
    client: ClientOut
    rating: RatingEnum
    rating_label: str
    comment: Optional[str] = None
    created_at: datetime

    @classmethod
    def from_orm(cls, rating: AverageRating) -> "AverageRatingOut":
        return cls(
            id=rating.id,
            service=ServiceOut.from_orm(rating.service),
            employee=EmployeeOut.from_orm(rating.employee),
            client=ClientOut.from_orm(rating.client),
            rating=rating.rating,
            rating_label=rating.get_rating_display(),
            comment=rating.comment,
            created_at=rating.created_at,
        )


class AverageRatingPrivateOut(Schema):
    """Avaliação privada — visão do dono (cliente) ou do admin, com campos de moderação."""
    id: uuid.UUID
    scheduling_id: uuid.UUID
    service: ServiceOut
    employee: EmployeeOut
    client: ClientOut
    rating: RatingEnum
    rating_label: str
    comment: Optional[str] = None
    is_authorized: bool
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_orm(cls, rating: AverageRating) -> "AverageRatingPrivateOut":
        return cls(
            id=rating.id,
            scheduling_id=rating.scheduling_id,
            service=ServiceOut.from_orm(rating.service),
            employee=EmployeeOut.from_orm(rating.employee),
            client=ClientOut.from_orm(rating.client),
            rating=rating.rating,
            rating_label=rating.get_rating_display(),
            comment=rating.comment,
            is_authorized=rating.is_authorized,
            created_at=rating.created_at,
            updated_at=rating.updated_at,
        )


class AverageRatingCreateIn(Schema):
    """
    Só pede `scheduling_id` + a nota/comentário. `service`, `employee` e
    `client` NUNCA vêm do payload — são sempre derivados do agendamento já
    validado (o client não tem como forjar um employee/service que não
    corresponde ao agendamento que ele está avaliando).
    """
    scheduling_id: uuid.UUID
    rating: RatingEnum
    comment: Optional[str] = None

    @field_validator("comment")
    @classmethod
    def validate_comment_create(cls, v: Optional[str]) -> Optional[str]:
        return _validate_comment(v)


class AverageRatingUpdateIn(Schema):
    rating: Optional[RatingEnum] = None
    comment: Optional[str] = None

    @field_validator("comment")
    @classmethod
    def validate_comment_update(cls, v: Optional[str]) -> Optional[str]:
        return _validate_comment(v)


class AverageRatingFilter(Schema):
    service_id: Optional[uuid.UUID] = None
    employee_id: Optional[uuid.UUID] = None
    client_id: Optional[uuid.UUID] = None
    rating: Optional[RatingEnum] = None
    is_authorized: Optional[bool] = None


class AverageRatingList(Schema):
    items: list[AverageRatingOut]


class AverageRatingPrivateList(Schema):
    items: list[AverageRatingPrivateOut]