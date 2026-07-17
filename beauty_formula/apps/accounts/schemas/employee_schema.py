import uuid
from datetime import date
from typing import Optional, List
from ninja import Schema, Field
from pydantic import field_validator
from phonenumbers import parse, is_valid_number, NumberParseException
from beauty_formula.apps.accounts.models import Employee
from beauty_formula.apps.accounts.schemas.user_schema import UserOut
from beauty_formula.apps.core.constants.gender import Gender

from enum import Enum


class GenderEnum(str, Enum):
    MALE = Gender.MALE
    FEMALE = Gender.FEMALE
    OTHER = Gender.OTHER


class EmployeeOut(Schema):
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
    bio: Optional[str] = None
      
    
    @classmethod
    def from_orm(cls, employee: Employee) -> "EmployeeOut":
        return cls(
            id=employee.id,
            user=UserOut.from_orm(employee.user),
            username=employee.username,
            first_name=employee.first_name,
            last_name=employee.last_name,
            instagram=employee.instagram,
            phone=employee.phone,
            gender=employee.gender,
            gender_label=employee.get_gender_display(),
            birth_date=employee.birth_date,
            bio=employee.bio,
            photo_url=employee.photo_url, 
           
        )


class EmployeeCreateIn(Schema):
    user_id: uuid.UUID
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    photo_url: Optional[str] = None  
    phone: Optional[str] = None
    birth_date: Optional[date] = None
    gender: GenderEnum
    instagram: Optional[str] = None
    bio: Optional[str] = None
      

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


class EmployeeUpdateIn(Schema):
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    gender: Optional[GenderEnum] = None
    phone: Optional[str] = None
    birth_date: Optional[date] = None
    instagram: Optional[str] = None
    bio: Optional[str] = None
        

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
        if v is not None and v.strip():
            try:
                parsed = parse(v, "BR")
                if not is_valid_number(parsed):
                    raise ValueError("Número de telefone inválido.")
            except NumberParseException:
                raise ValueError("Número de telefone inválido.")
        return 

class PromoteToEmployeeIn(Schema):
    """
    Não utilizado no path atual (user_id vem da URL), mantido apenas
    caso queira adicionar um campo `reason` opcional no futuro.
    """
    reason: Optional[str] = None



__all__ = [
    "EmployeeOut",
    "EmployeeCreateIn",
    "EmployeeUpdateIn",
    "PromoteToEmployeeIn",
]