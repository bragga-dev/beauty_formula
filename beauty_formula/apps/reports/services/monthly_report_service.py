"""
Regras do balanço mensal.

- Sem parâmetro: mês corrente, automático.
- `year`+`month`: mês específico (dinâmico — vem de
  `list_available_periods`/`list_generated_periods`, sem combo fixo).
- Sempre recalcula a partir dos dados vivos (`Scheduling`/
  `EmployeeCommission`) e grava (`update_or_create`) no
  `MonthlyReportSnapshot` — o snapshot é sempre um espelho atualizado do
  que existe agora, não um retrato congelado de quando foi gerado pela
  primeira vez, então reabrir o mês corrente sempre reflete o que mudou
  (ex.: uma comissão marcada como paga depois).
"""
import calendar
from datetime import date
from typing import Optional
from uuid import UUID

from django.db import transaction
from django.utils import timezone

from beauty_formula.apps.accounts.models.user import User
from beauty_formula.apps.reports.models.monthly_report_snapshot import MonthlyReportSnapshot
from beauty_formula.apps.reports.schemas.monthly_report_schema import AvailablePeriodOut, MonthlyBalanceOut
from beauty_formula.apps.reports.selectors.monthly_report_selector import (
    compute_employee_breakdown_data,
    compute_month_balance_data,
    get_snapshot,
    list_snapshots,
)


def _resolve_period(year: Optional[int], month: Optional[int]) -> tuple[int, int]:
    if year and month:
        if not (1 <= month <= 12):
            raise ValueError("Mês inválido.")
        return year, month

    today = timezone.localdate()
    return today.year, today.month


@transaction.atomic
def get_or_generate_monthly_balance(
    year: Optional[int] = None,
    month: Optional[int] = None,
    generated_by: Optional[User] = None,
) -> MonthlyBalanceOut:
    """Recalcula o balanço do mês resolvido e atualiza (ou cria) o snapshot persistido."""
    resolved_year, resolved_month = _resolve_period(year, month)
    last_day = calendar.monthrange(resolved_year, resolved_month)[1]
    start_date = date(resolved_year, resolved_month, 1)
    end_date = date(resolved_year, resolved_month, last_day)

    data = compute_month_balance_data(start_date=start_date, end_date=end_date)
    net_profit = data["total_revenue"] - data["total_commissions"]
    employee_breakdown = compute_employee_breakdown_data(start_date=start_date, end_date=end_date)

    snapshot, _created = MonthlyReportSnapshot.objects.update_or_create(
        year=resolved_year,
        month=resolved_month,
        defaults={
            "appointments_by_status": data["appointments_by_status"],
            "total_appointments": data["total_appointments"],
            "total_revenue": data["total_revenue"],
            "total_commissions": data["total_commissions"],
            "total_commissions_paid": data["total_commissions_paid"],
            "total_commissions_pending": data["total_commissions_pending"],
            "net_profit": net_profit,
            "employee_breakdown": employee_breakdown,
            "generated_by": generated_by,
        },
    )
    return MonthlyBalanceOut.from_orm(snapshot)


def get_monthly_balance_readonly(year: Optional[int] = None, month: Optional[int] = None) -> Optional[MonthlyBalanceOut]:
    """Lê o snapshot já gerado, sem recalcular — usado pela geração de PDF, que reaproveita o que a tela já mostrou."""
    resolved_year, resolved_month = _resolve_period(year, month)
    snapshot = get_snapshot(resolved_year, resolved_month)
    return MonthlyBalanceOut.from_orm(snapshot) if snapshot else None


def list_generated_periods() -> list[AvailablePeriodOut]:
    """Meses que já têm balanço gerado — popula o filtro do front dinamicamente."""
    return [AvailablePeriodOut(year=s.year, month=s.month) for s in list_snapshots()]