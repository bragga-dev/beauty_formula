from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Dict, Optional

from ninja import Schema

from beauty_formula.apps.reports.models.monthly_report_snapshot import MonthlyReportSnapshot


class MonthlyBalanceFilter(Schema):
    """Sem nada, o service assume o mês corrente. `year`+`month` pedem um mês específico e dinâmico."""
    year: Optional[int] = None
    month: Optional[int] = None


class MonthlyBalanceOut(Schema):
    id: uuid.UUID
    year: int
    month: int
    appointments_by_status: Dict[str, int]
    total_appointments: int
    total_revenue: Decimal
    total_commissions: Decimal
    total_commissions_paid: Decimal
    total_commissions_pending: Decimal
    net_profit: Decimal
    generated_at: datetime
    generated_by_name: Optional[str] = None

    @classmethod
    def from_orm(cls, snapshot: MonthlyReportSnapshot) -> "MonthlyBalanceOut":
        return cls(
            id=snapshot.id,
            year=snapshot.year,
            month=snapshot.month,
            appointments_by_status=snapshot.appointments_by_status,
            total_appointments=snapshot.total_appointments,
            total_revenue=snapshot.total_revenue,
            total_commissions=snapshot.total_commissions,
            total_commissions_paid=snapshot.total_commissions_paid,
            total_commissions_pending=snapshot.total_commissions_pending,
            net_profit=snapshot.net_profit,
            generated_at=snapshot.generated_at,
            generated_by_name=snapshot.generated_by.email if snapshot.generated_by_id else None,
        )


class AvailablePeriodOut(Schema):
    year: int
    month: int