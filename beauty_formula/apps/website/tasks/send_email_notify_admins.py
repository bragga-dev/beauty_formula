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
def send_email_notify_admins(self, full_name: str, email: str, subject: str, message: str, created_at: datetime, phone: str)-> None:
    """Envia notificação para os administradores"""
    from django.conf import settings
    
    # Pega o primeiro admin ou todos
    admin_email = settings.ADMIN_EMAIL 
    print("GGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGG", admin_email)
    
    context = {
        "full_name": full_name,
        "email": email,
        "subject": subject,
        "message": message,
        "phone": phone,
        "created_at":created_at,
    }
    
    send_html_email(
        subject=f"Novo contato: {subject}",
        to_email=admin_email,
        template_name="website/emails/admin_notification.html",
        context=context,
    )