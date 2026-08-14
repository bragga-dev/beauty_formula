import re
from decimal import Decimal
from typing import Optional
import uuid
from ninja import Schema
from pydantic import field_validator
from pydantic import Field
from beauty_formula.apps.website.models.product_models import Product


NAME_PATTERN = re.compile(r"^[\w\sÀ-ÿ.,'-]+$")


def _validate_price_non_negative(v: Optional[Decimal]) -> Optional[Decimal]:
    if v is not None and v < 0:
        raise ValueError("O preço não pode ser negativo.")
    return v


def _validate_name_format(v: Optional[str]) -> Optional[str]:
    if v is None:
        return v
    v = v.strip()
    if not NAME_PATTERN.match(v):
        raise ValueError("Nome inválido. Use letras, números, espaços e .,'-")
    return v


class ProductOut(Schema):
    id: uuid.UUID
    name: str
    description: Optional[str]
    price: Decimal
    image_url: str
    stock : int = Field(..., ge=0, description="Estoque do produto. Deve ser um número inteiro não negativo.")
    is_active : bool = Field(..., description="Indica se o produto está ativo ou não.")




class ProductPrivateOut(ProductOut):
    """
    Representação privada de um produto. Inclui todos os campos do ProductSchema.
    """
    pass


class ProductCreateIn(Schema):
    name: str
    description: Optional[str] = None
    price: Decimal
    stock: int = Field(..., ge=0, description="Estoque do produto. Deve ser um número inteiro não negativo.")

    _price_validator = field_validator("price")(_validate_price_non_negative)
    _name_validator = field_validator("name")(_validate_name_format)


class ProductUpdateIn(Schema):
    name: Optional[str] = None
    description: Optional[str] = None
    price: Optional[Decimal] = None
    stock: Optional[int] = Field(None, ge=0, description="Estoque do produto. Deve ser um número inteiro não negativo.")
    is_active: Optional[bool] = Field(None, description="Indica se o produto está ativo ou não.")

    _price_validator = field_validator("price")(_validate_price_non_negative)
    _name_validator = field_validator("name")(_validate_name_format)


class ProductFilter(Schema):
    name: Optional[str]
    min_price: Optional[Decimal]
    max_price: Optional[Decimal]
    is_active: Optional[bool]


class ProductDetailOut(ProductOut):
    """
    Representação detalhada de um produto. Inclui todos os campos do ProductSchema.
    """
    pass

class ProductListOut(Schema):
    products: list[ProductOut]