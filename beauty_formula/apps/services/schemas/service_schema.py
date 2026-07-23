import re
from decimal import Decimal
from typing import Optional
import uuid

from ninja import Schema
from pydantic import field_validator

from beauty_formula.apps.services.models.service import Service

NAME_PATTERN = re.compile(r"^[\w\sÀ-ÿ.,'-]+$")
MIN_DURATION_MINUTES = 1


def _validate_price_non_negative(v: Optional[Decimal]) -> Optional[Decimal]:
    if v is not None and v < 0:
        raise ValueError("O preço não pode ser negativo.")
    return v


def _validate_commission_range(v: Optional[Decimal]) -> Optional[Decimal]:
    if v is not None and (v < 0 or v > 100):
        raise ValueError("A comissão deve estar entre 0 e 100.")
    return v


def _validate_name_format(v: Optional[str]) -> Optional[str]:
    if v is None:
        return v
    v = v.strip()
    if not NAME_PATTERN.match(v):
        raise ValueError("Nome inválido. Use letras, números, espaços e .,'-")
    return v


def _validate_duration_minutes(v: Optional[int]) -> Optional[int]:
    if v is not None and v < MIN_DURATION_MINUTES:
        raise ValueError(f"A duração deve ser de pelo menos {MIN_DURATION_MINUTES} minuto.")
    return v


class ServiceOut(Schema):
    """
    Representação pública de um serviço. Deliberadamente NÃO inclui
    `commission_percentage` nem `total_bookings` — dado interno de
    negócio, não deveria ser exposto numa página pública.
    """
    id: uuid.UUID
    name: str
    description: Optional[str] = None
    price: Decimal
    image_url: str
    duration_minutes: int

    @staticmethod
    def resolve_duration_minutes(service: Service) -> int:
        return int(service.duration.total_seconds() // 60)


class ServiceCreateIn(Schema):
    name: str
    description: Optional[str] = None
    price: Decimal
    commission_percentage: Decimal = Decimal("70")
    duration_minutes: int = 30

    _price_validator = field_validator("price")(_validate_price_non_negative)
    _commission_validator = field_validator("commission_percentage")(_validate_commission_range)
    _name_validator = field_validator("name")(_validate_name_format)
    _duration_validator = field_validator("duration_minutes")(_validate_duration_minutes)


class ServiceUpdateIn(Schema):
    name: Optional[str] = None
    description: Optional[str] = None
    price: Optional[Decimal] = None
    commission_percentage: Optional[Decimal] = None
    duration_minutes: Optional[int] = None

    _price_validator = field_validator("price")(_validate_price_non_negative)
    _commission_validator = field_validator("commission_percentage")(_validate_commission_range)
    _name_validator = field_validator("name")(_validate_name_format)
    _duration_validator = field_validator("duration_minutes")(_validate_duration_minutes)


class ServiceFilter(Schema):
    search: Optional[str] = None


__all__ = ["ServiceOut", "ServiceCreateIn", "ServiceUpdateIn", "ServiceFilter"]