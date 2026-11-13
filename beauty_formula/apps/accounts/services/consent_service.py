"""
Consent Service — regras de consentimento (LGPD).

- Cadastro: aceite de Termos + Política é OBRIGATÓRIO; comunicações
  promocionais são opcionais e começam DESLIGADAS (nunca pré-marcadas).
- Toda mudança (aceite, novo aceite, revogação) grava uma linha em ConsentLog
  com versão, IP e user agent — prova do consentimento.
- Revogar é tão fácil quanto aceitar (art. 8º, §5º).
"""
from typing import Optional

from django.db import transaction
from django.utils import timezone

from beauty_formula.apps.accounts.models.consent_log import ConsentLog
from beauty_formula.apps.accounts.models.user import User
from beauty_formula.apps.accounts.repositories.consent_repository import (
    create_consent_log,
    list_consent_logs,
    save_user_consent,
)
from beauty_formula.apps.accounts.schemas.consent_schema import (
    ConsentAcceptIn,
    ConsentLogOut,
    ConsentStatusOut,
)
from beauty_formula.apps.core.exceptions.user import ConsentRequired
from beauty_formula.apps.legal import constants

Doc = ConsentLog.Document
Act = ConsentLog.Action


def _log(user: User, document: str, version: str, action: str, source: str, ip: Optional[str], user_agent: str) -> None:
    create_consent_log(
        user=user, document=document, version=version, action=action,
        source=source, ip_address=ip, user_agent=user_agent,
    )


def _record_documents(user: User, source: str, ip: Optional[str], user_agent: str) -> None:
    now = timezone.now()
    save_user_consent(
        user,
        terms_version=constants.TERMS_VERSION, terms_accepted_at=now,
        privacy_version=constants.PRIVACY_VERSION, privacy_accepted_at=now,
    )
    _log(user, Doc.TERMS, constants.TERMS_VERSION, Act.ACCEPTED, source, ip, user_agent)
    _log(user, Doc.PRIVACY, constants.PRIVACY_VERSION, Act.ACCEPTED, source, ip, user_agent)


def _apply_marketing(user: User, opt_in: bool, source: str, ip: Optional[str], user_agent: str) -> None:
    if user.marketing_opt_in == opt_in:
        return
    save_user_consent(user, marketing_opt_in=opt_in, marketing_opt_in_at=timezone.now())
    _log(user, Doc.MARKETING, "", Act.ACCEPTED if opt_in else Act.REVOKED, source, ip, user_agent)


@transaction.atomic
def record_signup_consent(
    user: User, *, marketing_opt_in: bool, source: str, ip: Optional[str], user_agent: str,
) -> User:
    """Chamado dentro do cadastro (e-mail/senha ou Google), na mesma transação."""
    _record_documents(user, source, ip, user_agent)
    _apply_marketing(user, marketing_opt_in, source, ip, user_agent)
    return user


@transaction.atomic
def accept_current_documents(user: User, data: ConsentAcceptIn, *, ip: Optional[str], user_agent: str) -> ConsentStatusOut:
    """Novo aceite (conta criada pelo admin ou documentos atualizados)."""
    if not (data.accept_terms and data.accept_privacy_policy):
        raise ConsentRequired()
    _record_documents(user, ConsentLog.Source.RE_ACCEPT, ip, user_agent)
    _apply_marketing(user, data.marketing_opt_in, ConsentLog.Source.RE_ACCEPT, ip, user_agent)
    return ConsentStatusOut.from_user(user)


@transaction.atomic
def set_marketing_consent(user: User, opt_in: bool, *, ip: Optional[str], user_agent: str) -> ConsentStatusOut:
    _apply_marketing(user, opt_in, ConsentLog.Source.SETTINGS, ip, user_agent)
    return ConsentStatusOut.from_user(user)


def get_consent_status(user: User) -> ConsentStatusOut:
    return ConsentStatusOut.from_user(user)


def list_consent_history(user: User):
    return list_consent_logs(user.id)


def serialize_history(user: User) -> list[ConsentLogOut]:
    return [ConsentLogOut.from_orm(log) for log in list_consent_history(user)]