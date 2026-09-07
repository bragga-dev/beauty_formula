# beauty_formula/apps/notifications/services/notification_service.py
"""
Service layer de Notification.

Convenção do projeto: quando um domínio (scheduling, payment, ratings...)
precisa notificar algo, ele chama um dos helpers `notify_*` passando o ID
do objeto de origem (scheduling_id, payment_id, refund_request_id...) —
nunca a instância — e é este módulo quem resolve o ID via selector do
domínio correspondente. Isso mantém o mesmo padrão já usado em chamadas
cross-app como `cancel_payment_for_scheduling(scheduling_id, ...)`.

Os helpers `notify_*` nunca deixam uma falha de notificação (registro não
encontrado, erro de validação) subir e derrubar a transação de negócio de
quem os chamou — o mesmo princípio já adotado para os e-mails assíncronos
em `payment_service` (ver `_request_refund_for_paid_scheduling`). Por isso
retornam `None` e apenas logam em caso de erro, em vez de propagar exceção.
"""
import logging
from typing import Optional
from uuid import UUID

from django.db import models

from beauty_formula.apps.accounts.models.user import User
from beauty_formula.apps.accounts.selectors.user_selector import get_user_by_id
from beauty_formula.apps.core.exceptions import NotificationNotFound, PermissionDenied, UserNotFound
from beauty_formula.apps.notifications.models.notification import Notification
from beauty_formula.apps.notifications.repositories.notification_repository import (
    create_notification as _create_notification,
    delete_notification as _delete_notification,
    mark_all_as_read as _mark_all_as_read,
    mark_as_read as _mark_as_read,
)
from beauty_formula.apps.notifications.selectors.notification_selector import (
    filter_notifications,
    get_notification_by_id,
    get_notifications_for_user,
    get_unread_count,
)

logger = logging.getLogger(__name__)

# ── URLs de ação por rota do front ──────────────────────────────────────────
# Cada `action_url` precisa apontar pra uma rota que EXISTE pro papel do
# `recipient`, senão o clique cai em 404 (rotas do front são segregadas por
# role — ver `AppRouter.tsx`: cliente, funcionário e admin têm páginas
# diferentes até pro mesmo agendamento). Centralizado aqui pra não espalhar
# strings de rota do front pelos helpers `notify_*`.
CLIENT_APPOINTMENT_URL = "/painel/meus-agendamentos/{id}"
EMPLOYEE_RATINGS_URL = "/painel/avaliacoes"
DASHBOARD_HOME_URL = "/painel"


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
    return _create_notification(
        recipient=recipient,
        notification_type=notification_type,
        title=title,
        body=body,
        action_url=action_url,
        actor=actor,
        target=target,
    )


def _safe_notify(notification_type: str, **kwargs) -> Optional[Notification]:
    """
    Envolve `notify()` para que uma falha aqui (registro de origem já
    excluído, corrida rara, etc.) nunca derrube a transação de negócio de
    quem chamou — só loga pra investigação.
    """
    try:
        return notify(notification_type=notification_type, **kwargs)
    except Exception:
        logger.exception("Falha ao criar notificação do tipo %s.", notification_type)
        return None


# ── Helpers de conveniência por domínio ─────────────────────────────────────
# Todos recebem o ID do objeto de origem — nunca a instância — e resolvem
# por conta própria via selector.

# =========================================================
# Agendamentos (Scheduling)
# =========================================================

def notify_scheduling_confirmed(scheduling_id: UUID, *, actor: Optional[User] = None) -> Optional[Notification]:
    from beauty_formula.apps.services.selectors.scheduling_selector import get_scheduling_by_id

    scheduling = get_scheduling_by_id(scheduling_id=scheduling_id)
    if scheduling is None:
        logger.warning("notify_scheduling_confirmed: agendamento %s não encontrado.", scheduling_id)
        return None
    return _safe_notify(
        Notification.NotificationType.SCHEDULING_CONFIRMED,
        recipient=scheduling.client.user,
        title="Agendamento confirmado",
        body=f"Seu horário de {scheduling.service.name} foi confirmado.",
        action_url=CLIENT_APPOINTMENT_URL.format(id=scheduling.id),
        actor=actor,
        target=scheduling,
    )


def notify_scheduling_cancelled(scheduling_id: UUID, *, actor: Optional[User] = None) -> Optional[Notification]:
    from beauty_formula.apps.services.selectors.scheduling_selector import get_scheduling_by_id

    scheduling = get_scheduling_by_id(scheduling_id=scheduling_id)
    if scheduling is None:
        logger.warning("notify_scheduling_cancelled: agendamento %s não encontrado.", scheduling_id)
        return None
    return _safe_notify(
        Notification.NotificationType.SCHEDULING_CANCELLED,
        recipient=scheduling.client.user,
        title="Agendamento cancelado",
        body=f"Seu horário de {scheduling.service.name} foi cancelado.",
        action_url=CLIENT_APPOINTMENT_URL.format(id=scheduling.id),
        actor=actor,
        target=scheduling,
    )


def notify_scheduling_rescheduled(scheduling_id: UUID, *, actor: Optional[User] = None) -> Optional[Notification]:
    from beauty_formula.apps.services.selectors.scheduling_selector import get_scheduling_by_id

    scheduling = get_scheduling_by_id(scheduling_id=scheduling_id)
    if scheduling is None:
        logger.warning("notify_scheduling_rescheduled: agendamento %s não encontrado.", scheduling_id)
        return None
    return _safe_notify(
        Notification.NotificationType.SCHEDULING_RESCHEDULED,
        recipient=scheduling.client.user,
        title="Agendamento reagendado",
        body=f"Seu horário de {scheduling.service.name} foi reagendado.",
        action_url=CLIENT_APPOINTMENT_URL.format(id=scheduling.id),
        actor=actor,
        target=scheduling,
    )


def notify_scheduling_reminder(scheduling_id: UUID) -> Optional[Notification]:
    from beauty_formula.apps.services.selectors.scheduling_selector import get_scheduling_by_id

    scheduling = get_scheduling_by_id(scheduling_id=scheduling_id)
    if scheduling is None:
        logger.warning("notify_scheduling_reminder: agendamento %s não encontrado.", scheduling_id)
        return None
    return _safe_notify(
        Notification.NotificationType.SCHEDULING_REMINDER,
        recipient=scheduling.client.user,
        title="Lembrete de agendamento",
        body=f"Seu atendimento de {scheduling.service.name} está próximo.",
        action_url=CLIENT_APPOINTMENT_URL.format(id=scheduling.id),
        target=scheduling,
    )


def notify_scheduling_complete(scheduling_id: UUID) -> Optional[Notification]:
    from beauty_formula.apps.services.selectors.scheduling_selector import get_scheduling_by_id

    scheduling = get_scheduling_by_id(scheduling_id=scheduling_id)
    if scheduling is None:
        logger.warning("notify_scheduling_complete: agendamento %s não encontrado.", scheduling_id)
        return None
    return _safe_notify(
        Notification.NotificationType.SCHEDULING_COMPLETE,
        recipient=scheduling.client.user,
        title="Agendamento concluído",
        body=f"Seu horário de {scheduling.service.name} foi concluído.",
        action_url=CLIENT_APPOINTMENT_URL.format(id=scheduling.id),
        target=scheduling,
    )


# =========================================================
# Avaliações (Rating) — pedido de avaliação após conclusão
# =========================================================

def notify_request_rating(scheduling_id: UUID) -> Optional[Notification]:
    """Convida o cliente a avaliar um agendamento recém-concluído (ainda sem avaliação)."""
    from beauty_formula.apps.services.selectors.scheduling_selector import get_scheduling_by_id

    scheduling = get_scheduling_by_id(scheduling_id=scheduling_id)
    if scheduling is None:
        logger.warning("notify_request_rating: agendamento %s não encontrado.", scheduling_id)
        return None
    return _safe_notify(
        Notification.NotificationType.REQUEST_RATING,
        recipient=scheduling.client.user,
        title="Avalie seu atendimento",
        body=f"Conte pra gente como foi seu atendimento de {scheduling.service.name}.",
        action_url=CLIENT_APPOINTMENT_URL.format(id=scheduling.id),
        target=scheduling,
    )


def notify_new_rating(rating_id: UUID) -> Optional[Notification]:
    """Avisa o profissional que ele recebeu uma nova avaliação do cliente."""
    from beauty_formula.apps.services.selectors.average_rating_selector import get_average_rating_by_id

    rating = get_average_rating_by_id(rating_id=rating_id)
    if rating is None:
        logger.warning("notify_new_rating: avaliação %s não encontrada.", rating_id)
        return None
    return _safe_notify(
        Notification.NotificationType.NEW_RATING,
        recipient=rating.employee.user,
        title="Nova avaliação recebida",
        body=f"Você recebeu uma avaliação de {rating.rating} estrela(s) para {rating.service.name}.",
        action_url=EMPLOYEE_RATINGS_URL,
        actor=rating.client.user,
        target=rating,
    )


# ===========================================================================
# Pagamento (Payment / RefundRequest)
# ===========================================================================

def notify_payment_received(payment_id: UUID) -> Optional[Notification]:
    from beauty_formula.apps.payment.selectors.payment_selector import get_payment_by_id

    payment = get_payment_by_id(payment_id=payment_id)
    if payment is None:
        logger.warning("notify_payment_received: pagamento %s não encontrado.", payment_id)
        return None
    return _safe_notify(
        Notification.NotificationType.PAYMENT_RECEIVED,
        recipient=payment.client.user,
        title="Pagamento recebido",
        body=f"Seu pagamento para {payment.scheduling.service.name} foi recebido com sucesso.",
        action_url=CLIENT_APPOINTMENT_URL.format(id=payment.scheduling.id),
        target=payment,
    )


def notify_refund_requested(refund_request_id: UUID, *, actor: Optional[User] = None) -> Optional[Notification]:
    from beauty_formula.apps.payment.selectors.refund_request_selector import get_refund_request_by_id

    refund_request = get_refund_request_by_id(refund_request_id)
    if refund_request is None:
        logger.warning("notify_refund_requested: pedido de reembolso %s não encontrado.", refund_request_id)
        return None
    return _safe_notify(
        Notification.NotificationType.REFUND_REQUESTED,
        recipient=refund_request.client.user,
        title="Reembolso solicitado",
        body=(
            f"Seu pedido de reembolso de {refund_request.payment.scheduling.service.name} "
            f"foi registrado e está em análise."
        ),
        action_url=CLIENT_APPOINTMENT_URL.format(id=refund_request.payment.scheduling.id),
        actor=actor,
        target=refund_request,
    )


def notify_refund_reviewed(refund_request_id: UUID, *, actor: Optional[User] = None) -> Optional[Notification]:
    from beauty_formula.apps.payment.selectors.refund_request_selector import get_refund_request_by_id
    from beauty_formula.apps.payment.models.refund_request_model import RefundRequest

    refund_request = get_refund_request_by_id(refund_request_id)
    if refund_request is None:
        logger.warning("notify_refund_reviewed: pedido de reembolso %s não encontrado.", refund_request_id)
        return None

    approved = refund_request.status == RefundRequest.RefundRequestStatus.APPROVED
    title = "Reembolso aprovado" if approved else "Reembolso recusado"
    body = (
        f"Seu pedido de reembolso de {refund_request.payment.scheduling.service.name} foi aprovado. "
        f"Valor a receber: R$ {refund_request.refund_value}."
        if approved
        else f"Seu pedido de reembolso de {refund_request.payment.scheduling.service.name} foi recusado."
    )
    return _safe_notify(
        Notification.NotificationType.REFUND_REVIEWED,
        recipient=refund_request.client.user,
        title=title,
        body=body,
        action_url=CLIENT_APPOINTMENT_URL.format(id=refund_request.payment.scheduling.id),
        actor=actor or refund_request.reviewed_by,
        target=refund_request,
    )


# ===========================================================================
# Contas (Accounts)
# ===========================================================================

def notify_employee_promoted(user_id: UUID, *, actor: Optional[User] = None) -> Optional[Notification]:
    user = get_user_by_id(user_id=user_id)
    if user is None:
        logger.warning("notify_employee_promoted: usuário %s não encontrado.", user_id)
        return None
    return _safe_notify(
        Notification.NotificationType.EMPLOYEE_PROMOTED,
        recipient=user,
        title="Você agora é um profissional",
        body="Seu cadastro foi promovido para funcionário. Bem-vindo(a) ao time!",
        action_url=DASHBOARD_HOME_URL,
        actor=actor,
        target=None,
    )


# ===========================================================================
# Sistema
# ===========================================================================

def notify_system(*, user_id: UUID, title: str, body: str = "", action_url: str = "") -> Optional[Notification]:
    user = get_user_by_id(user_id=user_id)
    if user is None:
        logger.warning("notify_system: usuário %s não encontrado.", user_id)
        return None
    return _safe_notify(
        Notification.NotificationType.SYSTEM,
        recipient=user,
        title=title,
        body=body,
        action_url=action_url,
        target=None,
    )


# ── Leitura / mutação de estado (com checagem de dono) ──────────────────────
# Estas SIM propagam exceção — são chamadas diretamente pela rota, que
# precisa saber que algo deu errado pra responder o status HTTP certo.

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


def mark_notification_as_read(*, user_id: UUID, notification_id: UUID) -> Notification:
    user = get_user_by_id(user_id=user_id)
    if user is None:
        raise UserNotFound()
    notification = get_notification_by_id(notification_id)
    if not notification:
        raise NotificationNotFound()
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
        raise NotificationNotFound()
    if notification.recipient_id != user.id:
        raise PermissionDenied("Você não pode excluir notificações de outro usuário.")
    _delete_notification(notification)


def list_all_notifications_for_admin(
    *, admin_user_id: UUID, target_user_id: Optional[UUID] = None, read: Optional[bool] = None
):
    admin = get_user_by_id(user_id=admin_user_id)
    if admin is None:
        raise UserNotFound()
    return filter_notifications(user_id=target_user_id, read=read)