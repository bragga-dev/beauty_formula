# beauty_formula/apps/notifications/repositories/notification_repository.py
"""
Repository de Notification — só persistência. Resolver `target` pra
instância (Scheduling, Payment, etc.) é responsabilidade do service.
"""
from typing import Optional
from uuid import UUID

from django.contrib.contenttypes.models import ContentType
from django.db import models, transaction
from django.utils import timezone

from beauty_formula.apps.accounts.models.user import User
from beauty_formula.apps.notifications.models.notification import Notification


@transaction.atomic
def create_notification(
    *,
    recipient: User,
    notification_type: str,
    title: str,
    body: str = "",
    action_url: str = "",
    actor: Optional[User] = None,
    target: Optional[models.Model] = None,
) -> Notification:
    content_type = ContentType.objects.get_for_model(target) if target else None
    return Notification.objects.create(
        recipient=recipient,
        actor=actor,
        notification_type=notification_type,
        title=title,
        body=body,
        action_url=action_url,
        content_type=content_type,
        object_id=target.pk if target else None,
    )


@transaction.atomic
def mark_as_read(notification: Notification) -> Notification:
    if not notification.is_read:
        notification.is_read = True
        notification.read_at = timezone.now()
        notification.save(update_fields=["is_read", "read_at"])
    return notification


@transaction.atomic
def mark_all_as_read(recipient_id: UUID) -> int:
    """Retorna quantas notificações foram marcadas como lidas."""
    return Notification.objects.filter(recipient_id=recipient_id, is_read=False).update(is_read=True, read_at=timezone.now())


@transaction.atomic
def delete_notification(notification: Notification) -> None:
    notification.delete()