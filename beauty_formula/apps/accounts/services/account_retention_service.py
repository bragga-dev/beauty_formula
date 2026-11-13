"""
Retenção de contas (LGPD — princípios da necessidade e da finalidade).

Contas de cliente que NUNCA confirmaram o e-mail e passaram de
settings.LEGAL_UNVERIFIED_ACCOUNT_RETENTION_DAYS são excluídas: não há mais
finalidade para guardar esses dados. Conta com vínculo protegido (ex.:
agendamento) não é apagada — fica para revisão manual.
"""
import logging
from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.db.models import ProtectedError
from django.utils import timezone

from beauty_formula.apps.accounts.selectors.user_selector import list_unverified_clients_older_than
from beauty_formula.apps.accounts.repositories.user_repository import delete_user

logger = logging.getLogger(__name__)


def purge_unverified_accounts() -> int:
    cutoff = timezone.now() - timedelta(days=settings.LEGAL_UNVERIFIED_ACCOUNT_RETENTION_DAYS)
    deleted = 0
    for user in list_unverified_clients_older_than(cutoff):
        try:
            with transaction.atomic():
                delete_user(user)
            deleted += 1
        except ProtectedError:
            logger.warning("Conta não verificada %s tem vínculos protegidos; mantida.", user.pk)
    return deleted