# beauty_formula/apps/notifications/models/notification.py
import uuid

from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils.translation import gettext_lazy as _


class Notification(models.Model):
    """
    Notificação de "sino" — um evento já renderizado (título/corpo prontos)
    endereçado a um User. `target` (GenericFK) é só pra navegação ao
    clicar; a listagem NUNCA depende de resolver o target pra exibir texto
    — title/body são gravados no momento da criação (igual feed do
    Instagram/Facebook: o texto não muda se o objeto original mudar depois).
    """

    class NotificationType(models.TextChoices):
        SCHEDULING_COMPLETE = "scheduling_complete", _("Agendamento concluído")
        SCHEDULING_CONFIRMED = "scheduling_confirmed", _("Agendamento confirmado")
        SCHEDULING_CANCELLED = "scheduling_cancelled", _("Agendamento cancelado")
        SCHEDULING_RESCHEDULED = "scheduling_rescheduled", _("Agendamento remarcado")
        SCHEDULING_REMINDER = "scheduling_reminder", _("Lembrete de agendamento")
        PAYMENT_RECEIVED = "payment_received", _("Pagamento recebido")
        REFUND_REQUESTED = "refund_requested", _("Reembolso solicitado")
        REFUND_REVIEWED = "refund_reviewed", _("Reembolso avaliado")
        REQUEST_RATING = "request_rating", _("Solicitação para avaliação")
        NEW_RATING = "new_rating", _("Nova avaliação recebida")
        EMPLOYEE_PROMOTED = "employee_promoted", _("Funcionário promovido")
        SYSTEM = "system", _("Aviso do sistema")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    recipient = models.ForeignKey("accounts.User", on_delete=models.CASCADE, related_name="notifications", verbose_name=_("Destinatário"))
    actor = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        related_name="triggered_notifications",
        null=True,
        blank=True,
        verbose_name=_("Autor do evento"),
        help_text=_("Quem originou o evento (ex: funcionário que cancelou), se houver."),
    )

    notification_type = models.CharField(_("Tipo"), max_length=32, choices=NotificationType.choices)
    title = models.CharField(_("Título"), max_length=140)
    body = models.CharField(_("Mensagem"), max_length=280, blank=True)
    action_url = models.CharField(_("URL de ação"), max_length=300, blank=True)

    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, null=True, blank=True)
    object_id = models.UUIDField(null=True, blank=True)
    target = GenericForeignKey("content_type", "object_id")

    is_read = models.BooleanField(_("Lida"), default=False)
    read_at = models.DateTimeField(_("Lida em"), null=True, blank=True)
    created_at = models.DateTimeField(_("Criado em"), auto_now_add=True)

    class Meta:
        verbose_name = _("Notificação")
        verbose_name_plural = _("Notificações")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["recipient", "is_read", "-created_at"]),
            models.Index(fields=["content_type", "object_id"]),
        ]

    def __str__(self):
        return f"{self.get_notification_type_display()} → {self.recipient}"