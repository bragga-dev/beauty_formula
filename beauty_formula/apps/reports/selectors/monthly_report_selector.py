"""
Queries de apoio ao balanço mensal.

`compute_month_balance_data` lê direto de `Scheduling` (todos os status,
pra contagem) e `EmployeeCommission` (competencia = mês) — não existe
nenhum dado próprio aqui, é só a leitura que alimenta o
`reports_service.get_or_generate_monthly_balance`, que grava o resultado
em `MonthlyReportSnapshot`.
"""
from datetime import date
from decimal import Decimal
from typing import Optional

from django.db.models import Count, DecimalField, Q, Sum, Value
from django.db.models.functions import Coalesce

from beauty_formula.apps.payment.models.employee_commission_model import EmployeeCommission
from beauty_formula.apps.reports.models.monthly_report_snapshot import MonthlyReportSnapshot
from beauty_formula.apps.services.models.scheduling import Scheduling

ZERO = Value(Decimal("0.00"), output_field=DecimalField(max_digits=12, decimal_places=2))


def get_snapshot(year: int, month: int) -> Optional[MonthlyReportSnapshot]:
    return MonthlyReportSnapshot.objects.filter(year=year, month=month).first()


def list_snapshots() -> list[MonthlyReportSnapshot]:
    """Todos os balanços já gerados — base do seletor dinâmico de mês/ano no front."""
    return list(MonthlyReportSnapshot.objects.order_by("-year", "-month"))


def compute_month_balance_data(*, start_date: date, end_date: date) -> dict:
    """
    Recalcula do zero, a partir dos dados vivos:
      - contagem de agendamentos por status (TODOS os status, pela
        `scheduled_time` dentro do mês — inclui cancelado/reagendado/etc,
        não só concluído);
      - faturamento: soma de `price_at_booking` só dos CONCLUÍDOS;
      - comissões: soma por status (`competencia` dentro do mês, mesma
        base de mês usada pra gerar a comissão em `employee_commission_service`).
    """
    schedulings = Scheduling.objects.filter(scheduled_time__date__gte=start_date, scheduled_time__date__lte=end_date)

    status_counts = schedulings.values("status").annotate(count=Count("id")).order_by()
    appointments_by_status = {row["status"]: row["count"] for row in status_counts}
    total_appointments = schedulings.count()

    total_revenue = schedulings.filter(status=Scheduling.SchedulingStatus.COMPLETED).aggregate(total=Coalesce(Sum("price_at_booking"), ZERO))["total"]

    commission_totals = EmployeeCommission.objects.filter(competencia__gte=start_date, competencia__lte=end_date).aggregate  \
    (
        total=Coalesce(Sum("commission_value"), ZERO),
        total_paid=Coalesce(Sum("commission_value", filter=Q(status=EmployeeCommission.CommissionStatus.PAID)), ZERO),
        total_pending=Coalesce(Sum("commission_value", filter=Q(status=EmployeeCommission.CommissionStatus.PENDING)), ZERO),
    )

    return \
    {
        "appointments_by_status": appointments_by_status,
        "total_appointments": total_appointments,
        "total_revenue": total_revenue,
        "total_commissions": commission_totals["total"],
        "total_commissions_paid": commission_totals["total_paid"],
        "total_commissions_pending": commission_totals["total_pending"],
    }