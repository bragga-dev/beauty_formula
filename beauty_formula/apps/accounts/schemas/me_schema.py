import uuid
from datetime import date
from typing import Optional
from ninja import Schema

from beauty_formula.apps.accounts.models.user import User
from beauty_formula.apps.accounts.models.client import Client
from beauty_formula.apps.accounts.models.employee import Employee
from beauty_formula.apps.accounts.schemas.user_schema import UserOut
from beauty_formula.apps.accounts.schemas.client_schema import GenderEnum


class ClientProfileOut(Schema):
    """Igual ao ClientOut, mas sem o `user` aninhado (evita duplicação dentro de MeOut)."""
    id: uuid.UUID
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
    def from_orm(cls, client: Client) -> "ClientProfileOut":
        return cls(
            id=client.id,
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


class EmployeeProfileOut(Schema):
    """Igual ao EmployeeOut, mas sem o `user` aninhado (evita duplicação dentro de MeOut)."""
    id: uuid.UUID
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
    def from_orm(cls, employee: Employee) -> "EmployeeProfileOut":
        return cls(
            id=employee.id,
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


class MeOut(Schema):
    """
    Resposta de GET /auth/me.
    `user` sempre vem preenchido (inclusive para admin, que não tem profile).
    `client` vem preenchido quando role=client, `employee` quando role=employee.
    """
    user:     UserOut
    client:   Optional[ClientProfileOut]   = None
    employee: Optional[EmployeeProfileOut] = None

    @classmethod
    def from_user(cls, user: User) -> "MeOut":
        client   = getattr(user, "client_profile", None)
        employee = getattr(user, "employee_profile", None)

        return cls(
            user=UserOut.from_orm(user),
            client=ClientProfileOut.from_orm(client) if client else None,
            employee=EmployeeProfileOut.from_orm(employee) if employee else None,
        )


__all__ = ["MeOut", "ClientProfileOut", "EmployeeProfileOut"]