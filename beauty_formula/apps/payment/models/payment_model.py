# payments/models/payment.py

import uuid
from decimal import Decimal
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator

class Payment(models.Model):
    class PaymentMode(models.TextChoices):
        UNDEFINED = "UNDEFINED", _("Indefinido")
        BOLETO = "BOLETO", _("Boleto")
        PIX = "PIX", _("Pix")
        CREDIT_CARD = "CREDIT_CARD", _("Cartão de Crédito")

    class PaymentStatus(models.TextChoices):
        PENDING = "PENDING", _("Pendente")
        RECEIVED = "RECEIVED", _("Recebido")
        CONFIRMED = "CONFIRMED", _("Confirmado")
        OVERDUE = "OVERDUE", _("Vencido")
        REFUNDED = "REFUNDED", _("Reembolsado")
        CANCELLED = "CANCELLED", _("Cancelado")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    scheduling = models.ForeignKey('service.Scheduling', on_delete=models.PROTECT, related_name="payments_scheduling")
    client = models.ForeignKey('accounts.Client', on_delete=models.PROTECT, related_name="payments_client")
    asaas_payment_id = models.CharField(_("ID da cobrança no Asaas"), max_length=50, blank=True, null=True, db_index=True)
    asaas_customer_id = models.CharField(_("ID do cliente no Asaas"), max_length=50, blank=True, null=True, db_index=True)
    value = models.DecimalField(_("Valor do Serviço"), max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    billing_type = models.CharField(_("Forma de Pagamento"), max_length=20, choices=PaymentMode.choices, default=PaymentMode.PIX, db_index=True)
    status = models.CharField(_("Status do Pagamento"), max_length=20, choices=PaymentStatus.choices, default=PaymentStatus.PENDING, db_index=True)
    due_date = models.DateField(_("Data limite para efetuar pagamento"))
    description = models.TextField(_("Descrição da cobrança"), max_length=500)
    external_reference = models.CharField(_("Referência externa"), max_length=100, blank=True, null=True, db_index=True)
    invoice_url = models.URLField(_("URL da fatura"), blank=True, null=True)
    bank_slip_url = models.URLField(_("URL do boleto"), blank=True, null=True)
    pix_qr_code = models.TextField(_("QR Code Pix"), blank=True, null=True)
    pix_copy_paste = models.TextField(_("Código Pix copia e cola"), blank=True, null=True)
    payment_date = models.DateTimeField(_("Data do pagamento"), blank=True, null=True)
    net_value = models.DecimalField(_("Valor líquido"), max_digits=10, decimal_places=2, blank=True, null=True)
    created_at = models.DateTimeField(_("Criado em"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Atualizado em"), auto_now=True)
    synced_with_asaas = models.BooleanField(_("Sincronizado com Asaas"), default=False)

    class Meta:
        ordering = ['-created_at']
        verbose_name = _("Pagamento")
        verbose_name_plural = _("Pagamentos")
        indexes = [
            models.Index(fields=['status', 'due_date']),
            models.Index(fields=['client', 'status']),
        ]

    def __str__(self):
        return f"Pagamento {self.id[:8]} - {self.client}"