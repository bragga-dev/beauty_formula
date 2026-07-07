



import uuid


from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _
from beauty_formula.apps.services.models.service import Service
from beauty_formula.apps.accounts.models.client import Client
from beauty_formula.apps.accounts.models.employee import Employee




class Scheduling(models.Model):
    class SchedulingStatus(models.TextChoices):
        PENDING = "pending", _("Pendente")
        CONFIRMED = "confirmed", _("Confirmado")
        CANCELED = "canceled", _("Cancelado")
        COMPLETED = "completed", _("Concluído")
        
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    service = models.ForeignKey(Service, on_delete=models.CASCADE, related_name="schedulings")
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name="schedulings")
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="schedulings")
    scheduled_time = models.DateTimeField(_("Horário agendado"))
    status = models.CharField(_("Status"), max_length=20, choices=SchedulingStatus.choices, default=SchedulingStatus.PENDING)
    created_at = models.DateTimeField(_("Criado em"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Atualizado em"), auto_now=True)

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
        ]

        constraints = [
            models.UniqueConstraint(fields=["service", "client", "employee", "scheduled_time"], name="unique_scheduling")
        ]   