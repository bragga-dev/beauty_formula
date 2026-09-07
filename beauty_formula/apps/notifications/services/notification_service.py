# beauty_formula/apps/notifications/services/notification_service.py
from typing import Optional
from uuid import UUID

from django.db import models
from django.shortcuts import get_object_or_404

from beauty_formula.apps.accounts.models.user import User
from beauty_formula.apps.core.exceptions import PermissionDenied
from beauty_formula.apps.notifications.models.notification import Notification
from beauty_formula.apps.notifications.schemas.notification_schema import (
    NotificationOut, 
    MarkAllReadOut, 
    UnreadCountOut,
    NotificationListOut,
    ) 
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
    list_all_notification,
)
from beauty_formula.apps.services.selectors.scheduling_selector import get_scheduling_by_id
from beauty_formula.apps.payment.selectors.payment_selector import get_payment_by_id
from beauty_formula.apps.services.selectors.average_rating_selector import get_average_rating_by_id
from beauty_formula.apps.accounts.selectors.user_selector import get_user_by_id
from beauty_formula.apps.core.exceptions.user import UserNotFound

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
    return _create_notification(
        recipient=recipient,
        notification_type=notification_type,
        title=title,
        body=body,
        action_url=action_url,
        actor=actor,
        target=target,
    )


# ── Helpers de conveniência por domínio ─────────────────────────────────────

# =========================================================
# Agendamentos (Scheduling)
# =========================================================
def notify_scheduling_confirmed(scheduling_id: UUID, *, actor: Optional[User] = None) -> NotificationOut:

    scheduling = get_scheduling_by_id(scheduling_id=scheduling_id)
    return notify(
        recipient=scheduling.client.user,
        notification_type=Notification.NotificationType.SCHEDULING_CONFIRMED,
        title="Agendamento confirmado",
        body=f"Seu horário de {scheduling.service.name} foi confirmado.",
        action_url=f"/appointments/{scheduling.id}",
        actor=actor,
        target=scheduling,
    )


def notify_scheduling_complete(scheduling_id: UUID, *, actor: Optional[User] = None) -> NotificationOut:

    scheduling = get_scheduling_by_id(scheduling_id=scheduling_id)
    return notify(
        recipient=scheduling.client.user,
        notification_type=Notification.NotificationType.SCHEDULING_COMPLETE,
        title="Agendamento concluído",
        body=f"Seu horário de {scheduling.service.name} foi concluído.",
        action_url=f"/appointments/{scheduling.id}",
        actor=actor,
        target=scheduling,
    )


def notify_scheduling_cancelled(scheduling_id: UUID, *, actor: Optional[User] = None) -> NotificationOut:
       
    scheduling = get_scheduling_by_id(scheduling_id=scheduling_id)
    return notify(
        recipient=scheduling.client.user,
        notification_type=Notification.NotificationType.SCHEDULING_CANCELLED,
        title="Agendamento cancelado",
        body=f"Seu horário de {scheduling.service.name} foi cancelado.",
        action_url=f"/appointments/{scheduling.id}",
        actor=actor,
        target=scheduling,
    )


def notify_scheduling_rescheduled(scheduling_id: UUID, *, actor: Optional[User] = None) -> NotificationOut:

    scheduling = get_scheduling_by_id(scheduling_id=scheduling_id)
    return notify(
        recipient=scheduling.client.user,
        notification_type=Notification.NotificationType.SCHEDULING_RESCHEDULED,
        title="Agendamento reagendado",
        body=f"Seu horário de {scheduling.service.name} foi reagendado.",
        action_url=f"/appointments/{scheduling.id}",
        actor=actor,
        target=scheduling,
    )


def notify_scheduling_reminder(scheduling_id: UUID, *, actor: Optional[User] = None) -> NotificationOut:

    scheduling = get_scheduling_by_id(scheduling_id=scheduling_id)
    return notify(
        recipient=scheduling.client.user,
        notification_type=Notification.NotificationType.SCHEDULING_REMINDER,
        title="Lembrete de agendamento",
        body=f"Seu atendimento de {scheduling.service.name} está próximo.",
        action_url=f"/appointments/{scheduling.id}",
        actor=actor,
        target=scheduling,
    )


# ===========================================================================
# Pagamento (Payment)
# ===========================================================================

def notify_payment_received(payment_id: UUID, *, actor: Optional[User] = None) -> NotificationOut:
    payment = get_payment_by_id(payment_id=payment_id)
    return notify(
        recipient=payment.client.user,
        notification_type=Notification.NotificationType.PAYMENT_RECEIVED,
        title="Pagamento recebido",
        body=f"Seu pagamento para {payment.scheduling.service.name} foi recebido com sucesso.",
        action_url=f"/payments/{payment.id}",
        actor=actor,
        target=payment,
    )


def notify_refund_requested(payment_id: UUID, *, actor: Optional[User] = None) -> NotificationOut:
    payment = get_payment_by_id(payment_id=payment_id)
    return notify(
        recipient=payment.client.user,
        notification_type=Notification.NotificationType.REFUND_REQUESTED,
        title="Reembolso solicitado",
        body=f"Seu pedido de reembolso para {payment.scheduling.service.name} foi solicitado.",
        action_url=f"/payments/{payment.id}",
        actor=actor,
        target=payment,
    )


def notify_refund_reviewed(payment_id: UUID, *, actor: Optional[User] = None) -> NotificationOut:
    
    payment = get_payment_by_id(payment_id=payment_id)
    return notify(
        recipient=payment.client.user,
        notification_type=Notification.NotificationType.REFUND_REVIEWED,
        title="Reembolso avaliado",
        body=f"Seu pedido de reembolso para {payment.scheduling.service.name} foi revisado.",
        action_url=f"/payments/{payment.id}",
        actor=actor,
        target=payment,
    )


# ===========================================================================
# Avaliações (Rating)
# ===========================================================================

def notify_request_rating(rating_id: UUID, *, actor: Optional[User] = None) -> NotificationOut:
    rating = get_average_rating_by_id(rating_id=rating_id)
    return notify(
        recipient=rating.scheduling.client.user,
        notification_type=Notification.NotificationType.REQUEST_RATING,
        title="Avalie seu atendimento",
        body=f"Por favor, avalie seu atendimento de {rating.scheduling.service.name}.",
        action_url=f"/ratings/{rating.id}",
        actor=actor,
        target=rating,
    )


def notify_new_rating(rating_id: UUID, *, actor: Optional[User] = None) -> NotificationOut:
    
    rating = get_average_rating_by_id(rating_id=rating_id)
    return notify(
        recipient=rating.scheduling.client.user,
        notification_type=Notification.NotificationType.NEW_RATING,
        title="Nova avaliação recebida",
        body=f"Você recebeu uma nova avaliação para {rating.scheduling.service.name}.",
        action_url=f"/ratings/{rating.id}",
        actor=actor,
        target=rating,
    )


# ===========================================================================
# Sistema
# ===========================================================================

def notify_system(user_id: UUID, title: str, body: str, action_url: str = "", *, actor: Optional[User] = None) -> NotificationOut:
    user = get_object_or_404(User, id=user_id)
    return notify(
        recipient=user,
        notification_type=Notification.NotificationType.SYSTEM,
        title=title,
        body=body,
        action_url=action_url,
        actor=actor,
        target=None,  
    )



# ── Leitura / mutação de estado (com checagem de dono) ──────────────────────

def list_notifications_for_user(*, user_id: UUID, unread_only: bool = False):
    user = get_user_by_id(user_id=user_id)
    if user is None:
        raise UserNotFound()
    return get_notifications_for_user(recipient_id=user.id, unread_only=unread_only)


def unread_count_for_user(*, user_id: UUID) -> int:
    user = get_user_by_id(user_id=user_id)
    if user is None:
        raise UserNotFound()
    return get_unread_count(recipient_id=user.id)


def mark_notification_as_read(*, user_id: UUID, notification_id: UUID) -> NotificationOut:
    user = get_user_by_id(user_id=user_id)
    if user is None:
        raise UserNotFound()
    notification = get_notification_by_id(notification_id)
    if not notification:
        raise ValueError("Notificação não encontrada.")
    if notification.recipient_id != user.id:
        raise PermissionDenied("Você não pode alterar notificações de outro usuário.")
    return _mark_as_read(notification)


def mark_all_notifications_as_read(*, user_id: UUID) -> int:
    user = get_user_by_id(user_id=user_id)
    if user is None:
        raise UserNotFound()
    return _mark_all_as_read(user.id)


def delete_notification(*, user_id: UUID, notification_id: UUID) -> None:
    user = get_user_by_id(user_id=user_id)
    if user is None:
        raise UserNotFound()
    notification = get_notification_by_id(notification_id)
    if not notification:
        raise ValueError("Notificação não encontrada.")
    if notification.recipient_id != user.id:
        raise PermissionDenied("Você não pode excluir notificações de outro usuário.")
    _delete_notification(notification)


def list_all_notification_by_admin(user_id: UUID, unread_only: bool = False) -> NotificationListOut:
    user = get_user_by_id(user_id=user_id)
    if user is None:
        raise UserNotFound()
    notifications = list_all_notification(unread_only=unread_only)
    return notifications