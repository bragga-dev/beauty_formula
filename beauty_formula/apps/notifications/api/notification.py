# beauty_formula/apps/notifications/api/notification.py
"""
Rotas de Notificações.

- Cliente/Usuário: visualiza, marca como lida e exclui suas próprias notificações.
- Admin: visão total com filtros (se necessário).
"""
from uuid import UUID

from django_ratelimit.decorators import ratelimit
from ninja import Router

from beauty_formula.apps.accounts.models.user import User
from beauty_formula.apps.accounts.schemas.user_schema import MessageOut
from beauty_formula.apps.core.permissions.auth_classes import AdminOnlyAuth, AllRolesAuth
from beauty_formula.apps.core.schemas.deafult_schema import PageOut
from beauty_formula.apps.core.utils.pagination import paginate_queryset
from beauty_formula.apps.notifications.schemas.notification_schema import (
    MarkAllReadOut,
    NotificationOut,
    UnreadCountOut,
)
from beauty_formula.apps.notifications.services.notification_service import (
    delete_notification,
    list_notifications_for_user,
    mark_all_notifications_as_read,
    mark_notification_as_read,
    unread_count_for_user,
)

router = Router()


# ═══════════════════════════════════════════════════════════════════════════════
# Usuário (qualquer role autenticado)
# ═══════════════════════════════════════════════════════════════════════════════

@router.get(
    "/",
    response={200: PageOut[NotificationOut], 401: MessageOut},
    auth=AllRolesAuth(),
    summary="Usuário lista as próprias notificações",
)
@ratelimit(key="user", rate="30/m", block=True)
def list_notifications_router(request, page: int = 1, page_size: int = 20, unread_only: bool = False):
    user: User = request.auth
    qs = list_notifications_for_user(user_id=user.id, unread_only=unread_only)
    return 200, paginate_queryset(qs, page, page_size, NotificationOut.from_orm)


@router.get(
    "/unread-count/",
    response={200: UnreadCountOut, 401: MessageOut},
    auth=AllRolesAuth(),
    summary="Usuário obtém a contagem de notificações não lidas",
)
@ratelimit(key="user", rate="30/m", block=True)
def unread_count(request):
    user: User = request.auth
    return 200, UnreadCountOut(unread_count=unread_count_for_user(user_id=user.id))


@router.post(
    "/{notification_id}/read/",
    response={200: NotificationOut, 404: MessageOut, 401: MessageOut},
    auth=AllRolesAuth(),
    summary="Usuário marca uma notificação como lida",
)
@ratelimit(key="user", rate="20/m", block=True)
def mark_as_read_router(request, notification_id: UUID):
    user: User = request.auth
    try:
        n = mark_notification_as_read(user_id=user.id, notification_id=notification_id)
        return 200, NotificationOut.from_orm(n)
    except Exception as e:
        return 404, {"detail": str(e)}


@router.post(
    "/read-all/",
    response={200: MarkAllReadOut, 401: MessageOut},
    auth=AllRolesAuth(),
    summary="Usuário marca todas as notificações como lidas",
)
@ratelimit(key="user", rate="10/m", block=True)
def mark_all_as_read_router(request):
    user: User = request.auth
    return 200, MarkAllReadOut(updated=mark_all_notifications_as_read(user_id=user.id))


@router.delete(
    "/{notification_id}/",
    response={200: dict, 404: MessageOut, 401: MessageOut},
    auth=AllRolesAuth(),
    summary="Usuário exclui uma notificação",
)
@ratelimit(key="user", rate="20/m", block=True)
def delete_notification_router(request, notification_id: UUID):
    user: User = request.auth
    try:
        delete_notification(user_id=user.id, notification_id=notification_id)
        return 200, {"success": True}
    except Exception as e:
        return 404, {"detail": str(e)}


# ═══════════════════════════════════════════════════════════════════════════════
# Admin (visão total) — se necessário
# ═══════════════════════════════════════════════════════════════════════════════

@router.get(
    "/admin/list-all",
    response={200: PageOut[NotificationOut], 401: MessageOut, 403: MessageOut},
    auth=AdminOnlyAuth(),
    summary="Admin lista todas as notificações com filtros",
)
@ratelimit(key="user", rate="30/m", block=True)
def list_all_notifications_router(
    request,
    user_id: UUID | None = None,
    read: bool | None = None,
    page: int = 1,
    page_size: int = 20,
):
    """
    Admin visualiza todas as notificações, com opção de filtrar por usuário e status de leitura.
    """
    from beauty_formula.apps.notifications.selectors.notification_selector import filter_notifications

    qs = filter_notifications(
        user_id=user_id,
        read=read,
    )
    return 200, paginate_queryset(qs, page, page_size, NotificationOut.from_orm)