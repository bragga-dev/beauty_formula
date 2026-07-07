



import uuid
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _
from beauty_formula.apps.services.models.employee_works_hours import EmployeeWorkingHours
from beauty_formula.apps.accounts.models.employee import Employee
from beauty_formula.apps.core.constants.block_type import BlockType


class EmployeeTimeOff(models.Model):
    """Modelo que representa folgas, férias e bloqueios de horário de um funcionário."""
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="time_off")
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    block_type = models.CharField(_("Tipo"), max_length=20, choices=BlockType.CHOICES, default=BlockType.OTHER)
    weekday = models.IntegerField(_("Dia da semana"), choices=EmployeeWorkingHours.Weekday.choices, null=True, blank=True)
    start_time = models.TimeField(_("Início"), null=True, blank=True)
    end_time = models.TimeField(_("Fim"), null=True, blank=True)
    start_datetime = models.DateTimeField(_("Início"), null=True, blank=True)
    end_datetime = models.DateTimeField(_("Fim"), null=True, blank=True)

    def clean(self):
        recurring = self.weekday is not None
        punctual = self.start_datetime is not None

        if recurring == punctual:
            raise ValidationError(_("Preencha weekday+start_time+end_time (recorrente) OU start_datetime+end_datetime (pontual), nunca os dois."))

        if recurring and (not self.start_time or not self.end_time or self.start_time >= self.end_time):
            raise ValidationError(_("Bloqueio recorrente exige start_time < end_time."))

        if punctual and (not self.end_datetime or self.end_datetime <= self.start_datetime):
            raise ValidationError(_("end_datetime deve ser depois de start_datetime."))

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = _("Bloqueio de horário")
        verbose_name_plural = _("Bloqueios de horário")
        indexes = [
            models.Index(fields=["employee", "weekday"]),
            models.Index(fields=["employee", "start_datetime"]),
        ]