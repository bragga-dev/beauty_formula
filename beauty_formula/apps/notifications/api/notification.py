# beauty_formula/apps/notifications/api/notification.py
from uuid import UUID

from ninja import Router

from beauty_formula.apps.core.permissions.auth_classes import AllRolesAuth
from beauty_formula.apps.core.schemas.deafult_schema import PageOut
from beauty_formula.apps.core.utils.pagination import paginate_queryset
from beauty_formula.apps.notifications.schemas.notification_schema import (
    MarkAllReadOut, NotificationOut, UnreadCountOut,
)
from beauty_formula.apps.notifications.services import notification_service

router = Router(auth=AllRolesAuth())


@router.get("/", response=PageOut[NotificationOut])
def list_notifications(request, page: int = 1, page_size: int = 20, unread_only: bool = False):
    qs = notification_service.list_notifications_for_user(user=request.auth, unread_only=unread_only)
    return paginate_queryset(qs, page, page_size, NotificationOut.from_orm)


@router.get("/unread-count/", response=UnreadCountOut)
def unread_count(request):
    return UnreadCountOut(unread_count=notification_service.unread_count_for_user(user=request.auth))


@router.post("/{notification_id}/read/", response=NotificationOut)
def mark_as_read(request, notification_id: UUID):
    n = notification_service.mark_notification_as_read(user=request.auth, notification_id=notification_id)
    return NotificationOut.from_orm(n)


@router.post("/read-all/", response=MarkAllReadOut)
def mark_all_as_read(request):
    return MarkAllReadOut(updated=notification_service.mark_all_notifications_as_read(user=request.auth))


@router.delete("/{notification_id}/")
def delete_notification(request, notification_id: UUID):
    notification_service.delete_notification(user=request.auth, notification_id=notification_id)
    return {"success": True}