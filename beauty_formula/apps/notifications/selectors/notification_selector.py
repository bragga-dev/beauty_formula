from typing import Optional
from uuid import UUID

from django.db.models import QuerySet

from beauty_formula.apps.notifications.models.notification import Notification

DEFAULT_RELATED = ("actor", "content_type")


def get_notification_by_id(notification_id: UUID) -> Optional[Notification]:
    return Notification.objects.select_related(*DEFAULT_RELATED).filter(id=notification_id).first()


def get_notifications_for_user(recipient_id: UUID, unread_only: bool = False) -> QuerySet[Notification]:
    qs = Notification.objects.select_related(*DEFAULT_RELATED).filter(recipient_id=recipient_id)
    if unread_only:
        qs = qs.filter(is_read=False)
    return qs.order_by("-created_at")


def get_unread_count(recipient_id: UUID) -> int:
    return Notification.objects.filter(recipient_id=recipient_id, is_read=False).count()


def list_all_notification(unread_only: bool = False) -> QuerySet[Notification]:
    qs = Notification.objects.select_related(*DEFAULT_RELATED).all()
    if unread_only:
        qs = qs.filter(is_read=False)
    return qs.order_by("-created_at")