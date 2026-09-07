

from datetime import datetime
from uuid import UUID

from ninja import Schema


class NotificationOut(Schema):
    id: UUID
    notification_type: str
    title: str
    body: str
    action_url: str
    is_read: bool
    created_at: datetime

    @staticmethod
    def from_orm(obj):
        return NotificationOut(
            id=obj.id, notification_type=obj.notification_type, title=obj.title,
            body=obj.body, action_url=obj.action_url, is_read=obj.is_read,
            created_at=obj.created_at,
        )


class UnreadCountOut(Schema):
    unread_count: int


class MarkAllReadOut(Schema):
    updated: int