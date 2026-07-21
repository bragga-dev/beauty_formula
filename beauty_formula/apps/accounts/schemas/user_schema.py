import uuid
from datetime import datetime
from typing import Optional

from ninja import Schema, Field
from ninja import UploadedFile
from pydantic import field_validator, model_validator, EmailStr
from enum import Enum

from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError

from beauty_formula.apps.accounts.models.user import User


# ── Enums ─────────────────────────────────────────────────────────────────────

class UserRoleEnum(str, Enum):
    ADMIN = User.UserRole.ADMIN
    CLIENT = User.UserRole.CLIENT
    EMPLOYEE = User.UserRole.EMPLOYEE


# ── Auth ─────────────────────────────────────────────────────────────────────

class RegisterIn(Schema):
    email:     EmailStr
    password:  str = Field(..., min_length=8)
    password2: str = Field(..., min_length=8)

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        try:
            validate_password(v)
        except DjangoValidationError as e:
            raise ValueError(", ".join(e.messages))
        return v

    @model_validator(mode="after")
    def passwords_match(self) -> "RegisterIn":
        if self.password != self.password2:
            raise ValueError("As senhas não coincidem.")
        return self


class RegisterEmployeeIn(Schema):
    """
    Cadastro de Funcionário pelo Admin. Diferente de `RegisterIn`
    (cadastro de Client), aqui o Admin informa apenas o e-mail: a senha
    é gerada automaticamente (ver `generate_temp_password`) e enviada
    ao funcionário por e-mail para o primeiro acesso.
    """
    email: EmailStr


class LoginIn(Schema):
    email:    str
    password: str


class GoogleLoginIn(Schema):
    """
    id_token: JWT (`credential`) emitido pelo Google Identity Services
    no frontend após o usuário se autenticar com a conta Google.
    """
    id_token: str = Field(..., min_length=10)


class TokenOut(Schema):
    access:  str
    refresh: str


class RefreshIn(Schema):
    refresh: str


class ChangePasswordIn(Schema):
    old_password: str
    new_password: str = Field(..., min_length=8)
    new_password2: str

    @field_validator("new_password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        try:
            validate_password(v)
        except DjangoValidationError as e:
            raise ValueError(", ".join(e.messages))
        return v

    @model_validator(mode="after")
    def passwords_match(self) -> "ChangePasswordIn":
        if self.new_password != self.new_password2:
            raise ValueError("As senhas não coincidem.")
        return self


class DeleteAccountIn(Schema):
    """Confirmação de senha exigida para exclusão da própria conta (LGPD)."""
    password: str


class PasswordResetRequestIn(Schema):
    email: str


class PasswordResetConfirmIn(Schema):
    uid:           str
    token:         str
    new_password:  str = Field(..., min_length=8)
    new_password2: str

    @model_validator(mode="after")
    def passwords_match(self) -> "PasswordResetConfirmIn":
        if self.new_password != self.new_password2:
            raise ValueError("As senhas não coincidem.")
        return self


# ── User ─────────────────────────────────────────────────────────────────────

class UserOut(Schema):
    id:          uuid.UUID
    email:       str
    role:        UserRoleEnum
    is_trusty:   bool
    is_active:   bool
    date_joined: datetime
    created_at:  datetime
    role_label: Optional[str] = None


    @classmethod
    def from_orm(cls, user: User) -> "UserOut":
        return cls(
            id=user.id,
            email=user.email,
            role=user.role,
            is_trusty=user.is_trusty,
            is_active=user.is_active,
            date_joined=user.date_joined,
            created_at=user.created_at,
            role_label=user.get_role_display(),
        )


class SessionOut(Schema):
    """Representa um refresh token ativo (uma sessão/dispositivo logado)."""
    id:         int
    created_at: Optional[datetime] = None
    expires_at: datetime

    @classmethod
    def from_orm(cls, token) -> "SessionOut":
        return cls(
            id=token.id,
            created_at=token.created_at,
            expires_at=token.expires_at,
        )


# ── Mensagem genérica (respostas simples) ───────────────────────────────────

class MessageOut(Schema):
    detail: str


__all__ = [
    "UserRoleEnum",
    "RegisterIn",
    "RegisterEmployeeIn",
    "LoginIn",
    "GoogleLoginIn",
    "TokenOut",
    "RefreshIn",
    "ChangePasswordIn",
    "DeleteAccountIn",
    "PasswordResetRequestIn",
    "PasswordResetConfirmIn",
    "UserOut",
    "SessionOut",
    "MessageOut",
]