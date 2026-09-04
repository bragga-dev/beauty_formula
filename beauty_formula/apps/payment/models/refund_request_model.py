import uuid
from decimal import Decimal

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Q
from django.utils.translation import gettext_lazy as _

from beauty_formula.apps.accounts.models.user import User


DEFAULT_CANCELLATION_FEE_PERCENTAGE = Decimal("10.00")


class RefundRequest(models.Model):
    class RefundRequestStatus(models.TextChoices):
        PENDING = "pending", _("Aguardando análise")
        APPROVED = "approved", _("Aprovado")
        REJECTED = "rejected", _("Rejeitado")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    payment = models.ForeignKey("payment.Payment", on_delete=models.PROTECT, related_name="refund_requests", verbose_name=_("Pagamento"),)
    client = models.ForeignKey("accounts.Client", on_delete=models.PROTECT, related_name="refund_requests", verbose_name=_("Cliente"),)
    requested_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name="refund_requests_made", verbose_name=_("Solicitado por"),
        help_text=_("Quem cancelou o agendamento que originou o pedido — cliente, funcionário ou admin."),
    )

    reason = models.TextField(_("Motivo do cancelamento"), blank=True, default="")
    original_value = models.DecimalField(_("Valor original"), max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))],)
    fee_percentage = models.DecimalField(_("Taxa de cancelamento (%)"), max_digits=5, decimal_places=2, default=DEFAULT_CANCELLATION_FEE_PERCENTAGE,
        validators=[MinValueValidator(Decimal("0.00")), MaxValueValidator(Decimal("100.00"))],)
    fee_value = models.DecimalField(_("Valor retido (taxa)"), max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal("0.00"))],)
    refund_value = models.DecimalField(_("Valor a devolver"), max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal("0.00"))],
        help_text=_("original_value - fee_value. É o valor que o admin manda pra Asaas ao aprovar."),
    )

    status = models.CharField(_("Status"), max_length=20, choices=RefundRequestStatus.choices, default=RefundRequestStatus.PENDING, db_index=True,)
    admin_notes = models.TextField(_("Observações do admin"), blank=True, default="")
    reviewed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="refund_requests_reviewed", verbose_name=_("Analisado por"),)
    reviewed_at = models.DateTimeField(_("Analisado em"), null=True, blank=True)
    created_at = models.DateTimeField(_("Criado em"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Atualizado em"), auto_now=True)

    class Meta:
        verbose_name = _("Pedido de reembolso")
        verbose_name_plural = _("Pedidos de reembolso")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "created_at"]),
            models.Index(fields=["client", "status"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["payment"],
                condition=Q(status="pending"),
                name="one_pending_refund_request_per_payment",
            ),
            models.CheckConstraint(condition=Q(refund_value__lte=models.F("original_value")), name="refund_value_lte_original_value",),]

    def __str__(self):
        return f"Reembolso {str(self.id)[:8]} - {self.client} - {self.get_status_display()}"