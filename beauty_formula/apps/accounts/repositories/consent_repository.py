"""Consent Repository — persistência da trilha de consentimentos."""
from typing import Optional
from uuid import UUID
from django.db.models import QuerySet

from beauty_formula.apps.accounts.models.consent_log import ConsentLog
from beauty_formula.apps.accounts.models.user import User


def create_consent_log(
    *,
    user: User,
    document: str,
    version: str,
    action: str,
    source: str,
    ip_address: Optional[str],
    user_agent: str,
) -> ConsentLog:
    return ConsentLog.objects.create(
        user=user, user_ref=user.id, document=document, version=version,
        action=action, source=source, ip_address=ip_address, user_agent=user_agent,
    )


def list_consent_logs(user_id: UUID) -> QuerySet[ConsentLog]:
    return ConsentLog.objects.filter(user_ref=user_id)


def save_user_consent(user: User, **fields) -> User:
    for attr, value in fields.items():
        setattr(user, attr, value)
    user.save(update_fields=list(fields))
    return user