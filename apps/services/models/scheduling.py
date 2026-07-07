



import uuid


from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _
from beauty_formula.apps.accounts.models.user import User
from beauty_formula.apps.services.models.service import Service
from beauty_formula.apps.accounts.models.client import Client
from beauty_formula.apps.accounts.models.employee import Employee




class Scheduling(models.Model):
    """Modelo que representa um agendamento de serviço entre um cliente e um funcionário."""
    class SchedulingStatus(models.TextChoices):
        PENDING = "pending", _("Pendente")
        CONFIRMED = "confirmed", _("Confirmado")
        CANCELED = "canceled", _("Cancelado")
        COMPLETED = "completed", _("Concluído")
        
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    service = models.ForeignKey(Service, on_delete=models.PROTECT, related_name="schedulings")
    client = models.ForeignKey(Client, on_delete=models.PROTECT, related_name="schedulings")
    employee = models.ForeignKey(Employee, on_delete=models.PROTECT, related_name="schedulings")
    scheduled_time = models.DateTimeField(_("Horário agendado"))
    status = models.CharField(_("Status"), max_length=20, choices=SchedulingStatus.choices, default=SchedulingStatus.PENDING)
    is_active = models.BooleanField(_("Ativo"), default=True, help_text=_("Desative em vez de deletar para não quebrar agendamentos antigos."))
    created_at = models.DateTimeField(_("Criado em"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Atualizado em"), auto_now=True)
    price_at_booking = models.DecimalField(_("Preço no momento do agendamento"), max_digits=10, decimal_places=2, editable=False)
    duration_at_booking = models.DurationField(_("Duração no momento do agendamento"), editable=False)
    notes = models.TextField(_("Observações"), blank=True, null=True)

    canceled_at = models.DateTimeField(_("Cancelado em"), blank=True, null=True)
    canceled_reason = models.CharField(_("Motivo do cancelamento"), max_length=255, blank=True, null=True)
    canceled_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="canceled_schedulings"
    )

    def clean(self):
        if not self.duration_at_booking:
            return
        end_time = self.scheduled_time + self.duration_at_booking
        conflict = Scheduling.objects.filter(
            employee=self.employee,
            status__in=[self.SchedulingStatus.PENDING, self.SchedulingStatus.CONFIRMED],
            scheduled_time__lt=end_time,
        ).exclude(pk=self.pk)
        for s in conflict:
            s_end = s.scheduled_time + s.duration_at_booking
            if s_end > self.scheduled_time:
                raise ValidationError(_("Funcionário já possui agendamento nesse horário."))

    def save(self, *args, **kwargs):
        if not self.pk:
            self.price_at_booking = self.service.price
            self.duration_at_booking = self.service.duration
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Agendamento {self.id} - Serviço: {self.service.name} - Cliente: {self.client.first_name} {self.client.last_name} - Funcionário: {self.employee.first_name} {self.employee.last_name} - Horário: {self.scheduled_time} - Status: {self.status}"

    class Meta:
        verbose_name = _("Agendamento")
        verbose_name_plural = _("Agendamentos")
        ordering = ["-scheduled_time"]
        indexes = [
            models.Index(fields=["service"]),
            models.Index(fields=["client"]),
            models.Index(fields=["employee"]),
            models.Index(fields=["scheduled_time"]),
            models.Index(fields=["status"]),
            models.Index(fields=["status, scheduled_time"]),
        ]

      