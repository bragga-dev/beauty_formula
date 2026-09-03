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

from beauty_formula.apps.accounts.models.employee import Employee
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

    total_revenue = schedulings.filter(status=Scheduling.SchedulingStatus.COMPLETED).aggregate(
        total=Coalesce(Sum("price_at_booking"), ZERO)
    )["total"]

    commission_totals = EmployeeCommission.objects.filter(
        competencia__gte=start_date, competencia__lte=end_date
    ).aggregate(
        total=Coalesce(Sum("commission_value"), ZERO),
        total_paid=Coalesce(Sum("commission_value", filter=Q(status=EmployeeCommission.CommissionStatus.PAID)), ZERO),
        total_pending=Coalesce(Sum("commission_value", filter=Q(status=EmployeeCommission.CommissionStatus.PENDING)), ZERO),
    )

    return {
        "appointments_by_status": appointments_by_status,
        "total_appointments": total_appointments,
        "total_revenue": total_revenue,
        "total_commissions": commission_totals["total"],
        "total_commissions_paid": commission_totals["total_paid"],
        "total_commissions_pending": commission_totals["total_pending"],
    }


def compute_employee_breakdown_data(*, start_date: date, end_date: date) -> list[dict]:
    """
    Balanço por funcionário dentro do mês: quantos atendimentos CONCLUÍDOS
    cada um fez, quanto faturou (`price_at_booking` dos concluídos) e o
    total/pago/pendente de comissão (`competencia` dentro do mês — mesma
    base usada no balanço geral). Um funcionário só aparece se teve pelo
    menos um atendimento concluído OU alguma comissão com competência no
    mês (cobre o caso raro de competência ajustada manualmente pra fora
    do mês do atendimento).
    """
    completed = (
        Scheduling.objects.filter(
            status=Scheduling.SchedulingStatus.COMPLETED,
            scheduled_time__date__gte=start_date,
            scheduled_time__date__lte=end_date,
        )
        .values("employee_id", "employee__first_name", "employee__last_name", "employee__username")
        .annotate(
            completed_appointments=Count("id"),
            revenue=Coalesce(Sum("price_at_booking"), ZERO),
        )
    )

    by_employee: dict = {}
    for row in completed:
        name = (f"{row['employee__first_name'] or ''} {row['employee__last_name'] or ''}").strip() \
            or row["employee__username"] or str(row["employee_id"])
        by_employee[row["employee_id"]] = {
            "employee_id": str(row["employee_id"]),
            "employee_name": name,
            "completed_appointments": row["completed_appointments"],
            "revenue": row["revenue"],
            "commission_total": Decimal("0.00"),
            "commission_paid": Decimal("0.00"),
            "commission_pending": Decimal("0.00"),
        }

    commissions = (
        EmployeeCommission.objects.filter(competencia__gte=start_date, competencia__lte=end_date)
        .values("employee_id", "employee__first_name", "employee__last_name", "employee__username")
        .annotate(
            commission_total=Coalesce(Sum("commission_value"), ZERO),
            commission_paid=Coalesce(Sum("commission_value", filter=Q(status=EmployeeCommission.CommissionStatus.PAID)), ZERO),
            commission_pending=Coalesce(Sum("commission_value", filter=Q(status=EmployeeCommission.CommissionStatus.PENDING)), ZERO),
        )
    )

    for row in commissions:
        entry = by_employee.get(row["employee_id"])
        if entry is None:
            name = (f"{row['employee__first_name'] or ''} {row['employee__last_name'] or ''}").strip() \
                or row["employee__username"] or str(row["employee_id"])
            entry = by_employee[row["employee_id"]] = {
                "employee_id": str(row["employee_id"]),
                "employee_name": name,
                "completed_appointments": 0,
                "revenue": Decimal("0.00"),
                "commission_total": Decimal("0.00"),
                "commission_paid": Decimal("0.00"),
                "commission_pending": Decimal("0.00"),
            }
        entry["commission_total"] = row["commission_total"]
        entry["commission_paid"] = row["commission_paid"]
        entry["commission_pending"] = row["commission_pending"]

    # `photo_url` é property do model (resolve via storage, com fallback
    # pro avatar padrão) — não dá pra puxar com `.values()` acima, então
    # busca os Employee reais só dos IDs que sobraram no breakdown.
    photo_by_id = {
        emp.id: emp.photo_url for emp in Employee.objects.filter(id__in=by_employee.keys())
    }
    for employee_id, entry in by_employee.items():
        entry["employee_photo_url"] = photo_by_id.get(employee_id)

    return sorted(by_employee.values(), key=lambda e: e["employee_name"].lower())


def compute_service_breakdown_data(*, start_date: date, end_date: date) -> list[dict]:
    """
    Quantidade de atendimentos CONCLUÍDOS por serviço dentro do mês, com o
    percentual de cada um sobre o total de concluídos — base do gráfico de
    pizza "quais serviços foram feitos" no front. Ordenado do mais pro
    menos frequente.
    """
    completed = (
        Scheduling.objects.filter(
            status=Scheduling.SchedulingStatus.COMPLETED,
            scheduled_time__date__gte=start_date,
            scheduled_time__date__lte=end_date,
        )
        .values("service_id", "service__name")
        .annotate(completed_appointments=Count("id"))
        .order_by("-completed_appointments")
    )

    rows = list(completed)
    total = sum(row["completed_appointments"] for row in rows)

    breakdown = []
    for row in rows:
        percentage = (Decimal(row["completed_appointments"]) / Decimal(total) * Decimal("100")) if total else Decimal("0.00")
        breakdown.append(
            {
                "service_id": str(row["service_id"]),
                "service_name": row["service__name"],
                "completed_appointments": row["completed_appointments"],
                "percentage": percentage.quantize(Decimal("0.01")),
            }
        )
    return breakdown