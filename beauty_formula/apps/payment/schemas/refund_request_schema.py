from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional

from ninja import Schema

from beauty_formula.apps.accounts.selectors.client_selector import get_client_full_name_display
from beauty_formula.apps.payment.models.refund_request_model import RefundRequest


class RefundRequestStatusEnum(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class RefundRequestOut(Schema):
    id: uuid.UUID
    payment_id: uuid.UUID
    client_id: uuid.UUID
    client_name: str
    scheduling_id: Optional[uuid.UUID] = None
    service_name: Optional[str] = None
    requested_by_name: str
    reason: str
    original_value: Decimal
    fee_percentage: Decimal
    fee_value: Decimal
    refund_value: Decimal
    status: RefundRequestStatusEnum
    admin_notes: str
    reviewed_by_name: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    created_at: datetime

    @classmethod
    def from_orm(cls, refund_request: RefundRequest) -> "RefundRequestOut":
        scheduling = refund_request.payment.scheduling
        return cls(
            id=refund_request.id,
            payment_id=refund_request.payment_id,
            client_id=refund_request.client_id,
            client_name=get_client_full_name_display(refund_request.client),
            scheduling_id=scheduling.id if scheduling else None,
            service_name=scheduling.service.name if scheduling else None,
            requested_by_name=refund_request.requested_by.email,
            reason=refund_request.reason,
            original_value=refund_request.original_value,
            fee_percentage=refund_request.fee_percentage,
            fee_value=refund_request.fee_value,
            refund_value=refund_request.refund_value,
            status=refund_request.status,
            admin_notes=refund_request.admin_notes,
            reviewed_by_name=refund_request.reviewed_by.email if refund_request.reviewed_by_id else None,
            reviewed_at=refund_request.reviewed_at,
            created_at=refund_request.created_at,
        )


class RefundRequestReviewIn(Schema):
    admin_notes: str = ""