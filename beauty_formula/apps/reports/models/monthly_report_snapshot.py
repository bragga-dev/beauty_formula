import uuid
from decimal import Decimal

from django.core.serializers.json import DjangoJSONEncoder
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _

from beauty_formula.apps.accounts.models.user import User


class MonthlyReportSnapshot(models.Model):
    """
    Balanço geral de UM mês (empresa toda, não por funcionário) — total de
    agendamentos por status, faturamento, comissões e lucro líquido.

    É um model "de leitura recalculável", não um registro que nasce de um
    evento de negócio: não existe `create()` direto, só
    `reports_service.get_or_generate_monthly_balance()`, que sempre
    recalcula a partir de `Scheduling`/`EmployeeCommission` (fonte de
    verdade dos dois domínios) e faz `update_or_create` aqui. Persistir
    serve pra dar à aba de relatórios do admin e à geração de PDF um
    registro estável pra ler/exportar, em vez de recalcular tudo a cada
    tela — sem duplicar a lógica de cálculo em outro lugar.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    year = models.PositiveSmallIntegerField(_("Ano"), validators=[MinValueValidator(2000)])
    month = models.PositiveSmallIntegerField(_("Mês"), validators=[MinValueValidator(1), MaxValueValidator(12)])
    appointments_by_status = models.JSONField(_("Agendamentos por status"), default=dict, help_text=_("Ex.: {\"completed\": 42, \"canceled\": 3, \"rescheduled\": 1, ...}"),)
    total_appointments = models.PositiveIntegerField(_("Total de agendamentos no mês"), default=0)
    total_revenue = models.DecimalField(
        _("Valor total arrecadado"), max_digits=12, decimal_places=2,
        default=Decimal("0.00"), validators=[MinValueValidator(Decimal("0.00"))],
        help_text=_("Soma do valor dos atendimentos CONCLUÍDOS no mês."),
    )
    total_commissions = models.DecimalField(
        _("Valor total em comissões"), max_digits=12, decimal_places=2,
        default=Decimal("0.00"), validators=[MinValueValidator(Decimal("0.00"))],
        help_text=_("Soma de todas as comissões geradas com competência neste mês, pagas ou não."),
    )
    total_commissions_paid = models.DecimalField(
        _("Comissões já pagas"), max_digits=12, decimal_places=2,
        default=Decimal("0.00"), validators=[MinValueValidator(Decimal("0.00"))],
    )
    total_commissions_pending = models.DecimalField(
        _("Comissões pendentes"), max_digits=12, decimal_places=2,
        default=Decimal("0.00"), validators=[MinValueValidator(Decimal("0.00"))],
    )
    net_profit = models.DecimalField(
        _("Lucro líquido"), max_digits=12, decimal_places=2, default=Decimal("0.00"),
        help_text=_("Valor total arrecadado − valor total em comissões."),
    )
    employee_breakdown = models.JSONField(
        _("Balanço por funcionário"), default=list, encoder=DjangoJSONEncoder,
        help_text=_(
            "Lista por funcionário no mês: id, nome, total de atendimentos "
            "concluídos, faturamento gerado, comissão total/paga/pendente. "
            "Ex.: [{\"employee_id\": \"...\", \"employee_name\": \"...\", "
            "\"completed_appointments\": 12, \"revenue\": \"600.00\", "
            "\"commission_total\": \"120.00\", \"commission_paid\": \"100.00\", "
            "\"commission_pending\": \"20.00\"}, ...]"
        ),
    )

    generated_at = models.DateTimeField(_("Gerado/atualizado em"), auto_now=True)
    generated_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name="monthly_report_snapshots",
        verbose_name=_("Gerado por"),
    )

    class Meta:
        verbose_name = _("Balanço mensal")
        verbose_name_plural = _("Balanços mensais")
        ordering = ["-year", "-month"]
        constraints = [
            models.UniqueConstraint(fields=["year", "month"], name="unique_monthly_report_snapshot"),
        ]
        indexes = [
            models.Index(fields=["year", "month"], name="monthly_report_year_month_idx"),
        ]

    def __str__(self):
        return f"Balanço {self.month:02d}/{self.year} — R$ {self.total_revenue}"