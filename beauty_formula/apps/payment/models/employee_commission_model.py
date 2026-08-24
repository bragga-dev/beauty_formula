import uuid
from datetime import date
from decimal import Decimal

from django.core.validators import (
    MaxValueValidator,
    MinValueValidator,
)
from django.db import models
from django.utils.translation import gettext_lazy as _

from beauty_formula.apps.accounts.models.user import User


class EmployeeCommission(models.Model):
    class CommissionStatus(models.TextChoices):
        PENDING = "pending", _("Pendente")
        PAID = "paid", _("Paga")
        CANCELED = "canceled", _("Cancelada")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    employee = models.ForeignKey("accounts.Employee", on_delete=models.PROTECT, related_name="commissions",  verbose_name=_("Funcionário"))
    scheduling = models.OneToOneField("services.Scheduling", on_delete=models.PROTECT, related_name="commission", verbose_name=_("Atendimento"))
    commission_value = models.DecimalField(_("Valor da comissão"), max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal("0.00"))])
    status = models.CharField(_("Status"), max_length=20, choices=CommissionStatus.choices, default=CommissionStatus.PENDING, db_index=True)
    paid_at = models.DateTimeField( _("Pago em"), null=True, blank=True)

    # ── Competência (mês de referência p/ auditoria e relatórios) ──────────
    # `competencia_original` é um snapshot imutável, calculado automaticamente
    # (a partir de scheduling.completed_at, ou scheduled_time como fallback)
    # no momento da criação — nunca muda depois, é a referência de auditoria.
    # `competencia` é o valor EFETIVO usado nos relatórios: nasce igual ao
    # original, mas o admin pode sobrescrever pra corrigir um caso pontual
    # (ex.: atendimento concluído com atraso já no mês seguinte, correção
    # retroativa). Sempre um DateField truncado no dia 1 do mês.
    competencia_original = models.DateField(_("Competência original (calculada)"), editable=False, default=date.today)
    competencia = models.DateField(_("Competência (mês de referência)"), db_index=True, default=date.today)
    competencia_changed_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name="commission_competencia_changes",
        verbose_name=_("Competência ajustada por"),
    )
    competencia_changed_at = models.DateTimeField(_("Competência ajustada em"), null=True, blank=True)

    created_at = models.DateTimeField(_("Criado em"), auto_now_add=True)
    updated_at = models.DateTimeField( _("Atualizado em"), auto_now=True)

    class Meta:
        verbose_name = _("Comissão")
        verbose_name_plural = _("Comissões")

        ordering = ["-created_at"]

        indexes = [
            models.Index(
                fields=["employee", "status"],
                name="commission_employee_status_idx",
            ),
            models.Index(
                fields=["status", "created_at"],
                name="commission_status_created_idx",
            ),
            models.Index(
                fields=["employee", "competencia"],
                name="commission_emp_competencia_idx",
            ),
            models.Index(
                fields=["competencia", "status"],
                name="comm_competencia_status_idx",
            ),
        ]

    def __str__(self):
        return (
            f"{self.employee} - "
            f"{self.commission_value} - "
            f"{self.get_status_display()}"
        )