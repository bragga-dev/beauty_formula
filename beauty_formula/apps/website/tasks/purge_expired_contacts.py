"""Task Celery — retenção dos contatos do site (LGPD)."""
import logging
from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task
def purge_expired_contacts_task() -> int:
    from beauty_formula.apps.website.services.contact_service import purge_expired_contacts
    deleted = purge_expired_contacts()
    logger.info("Retenção: %s contato(s) expirado(s) excluído(s).", deleted)
    return deleted