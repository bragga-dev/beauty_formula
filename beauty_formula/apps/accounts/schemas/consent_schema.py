import uuid
from datetime import datetime
from typing import Optional
from ninja import Schema

from beauty_formula.apps.accounts.models.consent_log import ConsentLog
from beauty_formula.apps.accounts.models.user import User
from beauty_formula.apps.legal import constants


class ConsentAcceptIn(Schema):
    """Aceite dos documentos vigentes (cadastros feitos pelo admin e mudança de versão)."""
    accept_terms: bool
    accept_privacy_policy: bool
    marketing_opt_in: bool = False


class MarketingConsentIn(Schema):
    opt_in: bool


class ConsentStatusOut(Schema):
    """
    Situação de consentimento do usuário logado (vem dentro de GET /auth/me).
    `needs_acceptance` = true quando a versão aceita é diferente da vigente
    (inclui contas criadas pelo admin, que ainda não aceitaram nada): o front
    deve exibir o aceite antes de liberar o uso.
    """
    needs_acceptance: bool
    terms_version_accepted: str
    terms_accepted_at: Optional[datetime] = None
    privacy_version_accepted: str
    privacy_accepted_at: Optional[datetime] = None
    current_terms_version: str
    current_privacy_version: str
    marketing_opt_in: bool
    marketing_opt_in_at: Optional[datetime] = None

    @classmethod
    def from_user(cls, user: User) -> "ConsentStatusOut":
        return cls(
            needs_acceptance=(
                user.terms_version != constants.TERMS_VERSION
                or user.privacy_version != constants.PRIVACY_VERSION
            ),
            terms_version_accepted=user.terms_version,
            terms_accepted_at=user.terms_accepted_at,
            privacy_version_accepted=user.privacy_version,
            privacy_accepted_at=user.privacy_accepted_at,
            current_terms_version=constants.TERMS_VERSION,
            current_privacy_version=constants.PRIVACY_VERSION,
            marketing_opt_in=user.marketing_opt_in,
            marketing_opt_in_at=user.marketing_opt_in_at,
        )


class ConsentLogOut(Schema):
    id: uuid.UUID
    document: str
    version: str
    action: str
    source: str
    ip_address: Optional[str] = None
    created_at: datetime

    @classmethod
    def from_orm(cls, log: ConsentLog) -> "ConsentLogOut":
        return cls(
            id=log.id, document=log.document, version=log.version, action=log.action,
            source=log.source, ip_address=log.ip_address, created_at=log.created_at,
        )


__all__ = ["ConsentAcceptIn", "MarketingConsentIn", "ConsentStatusOut", "ConsentLogOut"]