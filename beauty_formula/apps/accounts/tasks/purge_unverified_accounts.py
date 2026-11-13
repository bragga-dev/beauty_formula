"""Task Celery — retenção de contas nunca verificadas (LGPD)."""
import logging
from celery import shared_task

from beauty_formula.apps.accounts.services.account_retention_service import purge_unverified_accounts

logger = logging.getLogger(__name__)


@shared_task
def purge_unverified_accounts_task() -> int:
    deleted = purge_unverified_accounts()
    logger.info("Retenção: %s conta(s) não verificada(s) excluída(s).", deleted)
    return deleted