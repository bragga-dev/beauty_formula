# beauty_formula/apps/notifications/services/notification_service.py
from typing import Optional
from uuid import UUID

from django.db import models

from beauty_formula.apps.accounts.models.user import User
from beauty_formula.apps.core.exceptions import PermissionDenied
from beauty_formula.apps.notifications.models.notification import Notification
from beauty_formula.apps.notifications.repositories.notification_repository import (
    create_notification as _create_notification,
    delete_notification as _delete_notification,
    mark_all_as_read as _mark_all_as_read,
    mark_as_read as _mark_as_read,
)
from beauty_formula.apps.notifications.selectors.notification_selector import (
    get_notification_by_id,
    get_notifications_for_user,
    get_unread_count,
)


def notify(
    *,
    recipient: User,
    notification_type: str,
    title: str,
    body: str = "",
    action_url: str = "",
    actor: Optional[User] = None,
    target: Optional[models.Model] = None,
) -> Notification:
    """Ponto único de criação — todo domínio (scheduling, payment...) chama isso."""
    return _create_notification(recipient=recipient, notification_type=notification_type,
        title=title, body=body, action_url=action_url, actor=actor, target=target,
    )


# ── Helpers de conveniência por domínio ─────────────────────────────────────

def notify_scheduling_confirmed(scheduling) -> Notification:
    return notify(
        recipient=scheduling.client.user,
        notification_type=Notification.NotificationType.SCHEDULING_CONFIRMED,
        title="Agendamento confirmado",
        body=f"Seu horário de {scheduling.service.name} foi confirmado.",
        action_url=f"/appointments/{scheduling.id}",
        target=scheduling,
    )


def notify_scheduling_cancelled(scheduling, *, actor: Optional[User] = None) -> Notification:
    return notify(
        recipient=scheduling.client.user,
        notification_type=Notification.NotificationType.SCHEDULING_CANCELLED,
        title="Agendamento cancelado",
        body=f"Seu horário de {scheduling.service.name} foi cancelado.",
        action_url=f"/appointments/{scheduling.id}",
        actor=actor,
        target=scheduling,
    )


# ── Leitura / mutação de estado (com checagem de dono) ──────────────────────

def list_notifications_for_user(*, user: User, unread_only: bool = False):
    return get_notifications_for_user(recipient_id=user.id, unread_only=unread_only)


def unread_count_for_user(*, user: User) -> int:
    return get_unread_count(recipient_id=user.id)


def mark_notification_as_read(*, user: User, notification_id: UUID) -> Notification:
    notification = get_notification_by_id(notification_id)
    if not notification:
        raise ValueError("Notificação não encontrada.")
    if notification.recipient_id != user.id:
        raise PermissionDenied("Você não pode alterar notificações de outro usuário.")
    return _mark_as_read(notification)


def mark_all_notifications_as_read(*, user: User) -> int:
    return _mark_all_as_read(user.id)


def delete_notification(*, user: User, notification_id: UUID) -> None:
    notification = get_notification_by_id(notification_id)
    if not notification:
        raise ValueError("Notificação não encontrada.")
    if notification.recipient_id != user.id:
        raise PermissionDenied("Você não pode excluir notificações de outro usuário.")
    _delete_notification(notification)