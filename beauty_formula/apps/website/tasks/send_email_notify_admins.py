"""
Tasks Celery — envio de e-mails para client anomino após envio de formulário de contato
"""

import logging
from celery import shared_task
from datetime import datetime
from django.conf import settings
from beauty_formula.apps.core.emails.sender import send_html_email
logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
)
def send_email_notify_admins(self, full_name: str, email: str, subject: str, message: str, created_at: datetime, phone: str) -> None:
    """Envia notificação para os administradores sobre um novo contato recebido."""
    try:
        admin_email = settings.ADMIN_EMAIL

        context = {
            "full_name": full_name,
            "email": email,
            "subject": subject,
            "message": message,
            "phone": phone,
            "created_at": created_at,
            "admin_contacts_url": f"{settings.FRONTEND_URL}/painel/contatos",
        }

        send_html_email(
            subject=f"Novo contato: {subject}",
            to_email=admin_email,
            template_name="website/emails/admin_notification.html",
            context=context,
        )

        logger.info("Admin notification email sent to %s (contact from %s)", admin_email, email)

    except Exception as exc:
        logger.exception("Falha ao enviar e-mail de notificação para o admin (contato de %s): %s", email, str(exc))
        raise self.retry(exc=exc)