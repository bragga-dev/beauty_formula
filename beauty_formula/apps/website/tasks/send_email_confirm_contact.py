"""
Tasks Celery — envio de e-mails para client anomino após envio de formulário de contato
"""

import logging
from celery import shared_task
from datetime import datetime
from beauty_formula.apps.core.emails.sender import send_html_email
logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
)
def send_email_confirm_contact(self, full_name: str, email: str, subject: str, message: str, created_at: datetime, phone: str) -> None:
    """
    Notifica o client anonimo sobre a tentativa de contato
    """
    try:

        context = {

            "full_name": full_name,
            "email": email,
            "subject": subject,
            "message": message,
            "created_at": created_at,
            "phone": phone,
            
        }

        send_html_email(
            subject="Contato — Fórmula da Beleza",
            to_email=email,
            template_name="website/emails/send_email_confirm_contact.html",
            context=context,
        )

        logger.info(f"Email enviado com sucesso para {email}")

    except Exception as exc:
        logger.exception("Falha ao enviar e-mail de confirmação para %s (%s): %s", full_name, email, str(exc))
        raise self.retry(exc=exc)