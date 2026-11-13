import re
from datetime import datetime
from typing import Optional
import uuid

from ninja import Schema
from pydantic import field_validator, model_validator, Field

from beauty_formula.apps.website.models.contact_models import Contact


NAME_PATTERN = re.compile(r"^[\w\sÀ-ÿ.,'-]+$")
PHONE_PATTERN = re.compile(r"^\+?\d{8,15}$")


def _validate_name_format(v: str) -> str:
    v = v.strip()
    if not NAME_PATTERN.match(v):
        raise ValueError("Nome inválido. Use letras, números, espaços e .,'-")
    return v


def _validate_phone_format(v: str) -> str:
    digits_only = re.sub(r"[\s()-]", "", v)
    if not PHONE_PATTERN.match(digits_only):
        raise ValueError("Telefone inválido. Use apenas números (com DDD), 8 a 15 dígitos.")
    return v


class ContactOut(Schema):
    id: uuid.UUID
    full_name: str
    subject: Contact.ContactSubject
    message: str
    email: str
    phone: str
    status: Contact.ContactStatus
    created_at: datetime


class ContactCreateIn(Schema):
    full_name: str
    subject: Contact.ContactSubject = Contact.ContactSubject.OTHER
    message: str = Field(..., min_length=1, max_length=5000)
    email: str
    phone: str
    accept_privacy_policy: bool

    _name_validator = field_validator("full_name")(_validate_name_format)
    _phone_validator = field_validator("phone")(_validate_phone_format)

    @model_validator(mode="after")
    def privacy_accepted(self) -> "ContactCreateIn":
        if not self.accept_privacy_policy:
            raise ValueError("É necessário aceitar a Política de Privacidade para enviar a mensagem.")
        return self


class ContactUpdateIn(Schema):
    status: Contact.ContactStatus


class ContactFilter(Schema):
    search: Optional[str] = None
    status: Optional[Contact.ContactStatus] = None
    subject: Optional[Contact.ContactSubject] = None