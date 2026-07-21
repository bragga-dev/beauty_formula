import uuid
from datetime import date
from typing import Optional
from ninja import Schema, Field
from pydantic import field_validator
import re
from beauty_formula.apps.accounts.models import Client
from beauty_formula.apps.accounts.schemas.user_schema import UserOut
from beauty_formula.apps.core.constants.gender import Gender
from phonenumbers import parse, is_valid_number, NumberParseException
from enum import Enum


class GenderEnum(str, Enum):
    MALE = Gender.MALE
    FEMALE = Gender.FEMALE
    OTHER = Gender.OTHER


class ClientOut(Schema):
    id: uuid.UUID
    user: UserOut
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    instagram: Optional[str] = None
    phone: Optional[str] = None 
    photo_url: Optional[str] = None
    gender: GenderEnum
    gender_label: str
    birth_date: Optional[date] = None  
    
    @classmethod
    def from_orm(cls, client: Client) -> "ClientOut":
        return cls(
            id=client.id,
            user=UserOut.from_orm(client.user),
            username=client.username,
            first_name=client.first_name,
            last_name=client.last_name,
            instagram=client.instagram,
            phone=str(client.phone) if client.phone else None,  
            gender=client.gender,
            gender_label=client.get_gender_display(),
            birth_date=client.birth_date,
            photo_url=client.photo_url,  
        )


class ClientCreateIn(Schema):
    user_id: uuid.UUID
    username: str = Field(..., min_length=2, max_length=150)
    first_name: str = Field(..., min_length=2, max_length=255)
    last_name: str = Field(..., min_length=2, max_length=255)
    photo_url: Optional[str] = None  
    phone: Optional[str] = None  
    birth_date: Optional[date] = None 
    gender: Optional[GenderEnum] = None
    instagram: Optional[str] = None

    @field_validator("birth_date")
    @classmethod
    def birth_not_future(cls, v: Optional[date]) -> Optional[date]:
        if v and v > date.today():
            raise ValueError("Data de nascimento não pode ser no futuro.")
        return v

    @field_validator("username")
    @classmethod
    def username_format(cls, v: str) -> str:
        import re
        if not re.match(r'^[\w.@+-]+$', v):
            raise ValueError("Username inválido. Use apenas letras, números e @/./+/-/_.")
        return v
    
    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: Optional[str]) -> Optional[str]:
        if v:
            cleaned = re.sub(r'[^\d+]', '', v)
            if len(cleaned) < 10: 
                raise ValueError("Número de telefone inválido.")
        return v


class ClientUpdateIn(Schema):
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    gender: Optional[GenderEnum] = None
    phone: Optional[str] = None
    birth_date: Optional[date] = None  
    instagram: Optional[str] = None 

    @field_validator("birth_date")
    @classmethod
    def birth_not_future(cls, v: Optional[date]) -> Optional[date]:
        if v and v > date.today():
            raise ValueError("Data de nascimento não pode ser no futuro.")
        return v

    @field_validator("username")
    @classmethod
    def username_format(cls, v: Optional[str]) -> Optional[str]:
        if v:
            import re
            if not re.match(r'^[\w.@+-]+$', v):
                raise ValueError("Username inválido. Use apenas letras, números e @/./+/-/_.")
        return v
    
    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: Optional[str]) -> Optional[str]:
        if v:
            cleaned = re.sub(r'[^\d+]', '', v)
            if len(cleaned) < 10: 
                raise ValueError("Número de telefone inválido.")
        return v


__all__ = [

    "ClientOut",
    "ClientCreateIn",
    "ClientUpdateIn",
]