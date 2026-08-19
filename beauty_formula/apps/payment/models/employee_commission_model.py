import uuid
from decimal import Decimal

from django.core.validators import (
    MaxValueValidator,
    MinValueValidator,
)
from django.db import models
from django.utils.translation import gettext_lazy as _


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
        ]

    def __str__(self):
        return (
            f"{self.employee} - "
            f"{self.commission_value} - "
            f"{self.get_status_display()}"
        )