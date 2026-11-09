import uuid
from typing import Optional
from ninja import Schema
from pydantic import EmailStr

from beauty_formula.apps.accounts.models.manager import Manager
from beauty_formula.apps.accounts.schemas.user_schema import UserOut


class ManagerOut(Schema):
    id: uuid.UUID
    user: UserOut
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    photo_url: Optional[str] = None

    @classmethod
    def from_orm(cls, manager: Manager) -> "ManagerOut":
        return cls(
            id=manager.id,
            user=UserOut.from_orm(manager.user),
            first_name=manager.first_name,
            last_name=manager.last_name,
            photo_url=manager.photo_url,
        )


class ManagerCreateIn(Schema):
    """
    Cadastro de Gerente pelo Admin root. A senha é gerada automaticamente
    e enviada por e-mail para o primeiro acesso.
    """
    email: EmailStr
    first_name: Optional[str] = None
    last_name: Optional[str] = None


class ManagerUpdateIn(Schema):
    first_name: Optional[str] = None
    last_name: Optional[str] = None