"""
Rotas de relatórios — só admin.

- GET /reports/monthly-balance: sem parâmetros, mês corrente automático;
  `year`+`month` para um mês específico. Sempre recalcula e atualiza o
  snapshot (é a rota que a aba "Relatórios" do admin chama ao abrir).
- GET /reports/monthly-balance/history: meses que já têm balanço gerado
  — popula o filtro de período do front dinamicamente.
- GET /reports/monthly-balance/pdf: exporta o balanço em PDF. Lê o
  snapshot já gerado (não recalcula de novo) — se o mês pedido ainda não
  foi aberto na tela nenhuma vez, gera na hora antes de exportar.
"""
from typing import Optional

from django.http import HttpResponse
from django_ratelimit.decorators import ratelimit
from ninja import Query, Router

from beauty_formula.apps.accounts.schemas.user_schema import MessageOut
from beauty_formula.apps.core.permissions.auth_classes import AdminOnlyAuth
from beauty_formula.apps.core.services.pdf_service import render_pdf_from_template
from beauty_formula.apps.reports.schemas.monthly_report_schema import (
    AvailablePeriodOut,
    MonthlyBalanceFilter,
    MonthlyBalanceOut,
)
from beauty_formula.apps.reports.services.monthly_report_service import (
    get_or_generate_monthly_balance,
    list_generated_periods,
)
from beauty_formula.apps.services.models.scheduling import Scheduling

router = Router()

STATUS_LABELS = dict(Scheduling.SchedulingStatus.choices)
MONTH_LABELS = [
    "", "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
    "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro",
]


@router.get(
    "/monthly-balance",
    response={200: MonthlyBalanceOut, 400: MessageOut},
    auth=AdminOnlyAuth(),
    summary="Balanço geral do mês — agendamentos por status, faturamento, comissões e lucro líquido",
    description="Sem parâmetros, devolve (e atualiza) o balanço do mês corrente automaticamente. Informe `year`+`month` para um mês específico.",
)
@ratelimit(key="user", rate="30/m", block=True)
def get_monthly_balance_router(request, filters: Query[MonthlyBalanceFilter]):
    try:
        balance = get_or_generate_monthly_balance(year=filters.year, month=filters.month, generated_by=request.auth)
        return 200, balance
    except ValueError as e:
        return 400, {"detail": str(e)}


@router.get(
    "/monthly-balance/history",
    response={200: list[AvailablePeriodOut]},
    auth=AdminOnlyAuth(),
    summary="Meses que já têm balanço gerado (filtro dinâmico do front)",
)
@ratelimit(key="user", rate="30/m", block=True)
def get_monthly_balance_history_router(request):
    return 200, list_generated_periods()


@router.get(
    "/monthly-balance/pdf",
    auth=AdminOnlyAuth(),
    summary="Exporta o balanço do mês em PDF",
    description="Sem parâmetros, exporta o mês corrente. Se o mês ainda não tiver balanço gerado, gera na hora.",
)
@ratelimit(key="user", rate="15/m", block=True)
def get_monthly_balance_pdf_router(request, year: Optional[int] = None, month: Optional[int] = None):
    balance = get_or_generate_monthly_balance(year=year, month=month, generated_by=request.auth)

    status_rows = [
        {"label": STATUS_LABELS.get(status, status), "count": count}
        for status, count in balance.appointments_by_status.items()
    ]

    pdf_bytes = render_pdf_from_template(
        "reports/monthly_balance_pdf.html",
        {
            "year": balance.year,
            "month_label": MONTH_LABELS[balance.month],
            "generated_at": balance.generated_at.strftime("%d/%m/%Y %H:%M"),
            "generated_by_name": balance.generated_by_name,
            "total_appointments": balance.total_appointments,
            "total_revenue": balance.total_revenue,
            "total_commissions": balance.total_commissions,
            "total_commissions_paid": balance.total_commissions_paid,
            "total_commissions_pending": balance.total_commissions_pending,
            "net_profit": balance.net_profit,
            "status_rows": status_rows,
        },
    )

    response = HttpResponse(pdf_bytes, content_type="application/pdf")
    filename = f"balanco-{balance.year}-{balance.month:02d}.pdf"
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response