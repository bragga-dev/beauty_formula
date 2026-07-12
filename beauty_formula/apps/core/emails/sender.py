# core/emails/sender.py
import logging
from typing import Any

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags

logger = logging.getLogger(__name__)


def send_html_email(
    subject: str,
    to_email: str,
    template_name: str,
    context: dict[str, Any],
    from_email: str | None = None,
) -> None:
    """Envia email com HTML e fallback em texto puro."""
    from_email = from_email or settings.DEFAULT_FROM_EMAIL
    html_content = render_to_string(template_name, context)
    text_content = strip_tags(html_content)

    email = EmailMultiAlternatives(
        subject=subject,
        body=text_content,
        from_email=from_email,
        to=[to_email],
    )
    email.attach_alternative(html_content, "text/html")
    email.send(fail_silently=False)

    logger.info("Email enviado para %s — Assunto: %s", to_email, subject)