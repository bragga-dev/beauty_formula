
import uuid
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _
from beauty_formula.apps.accounts.models.employee import Employee




class EmployeeWorkingHours(models.Model):
    """Modelo que representa o horário de trabalho de um funcionário."""
    class Weekday(models.IntegerChoices):
        MONDAY = 0, _("Segunda")
        TUESDAY = 1, _("Terça")
        WEDNESDAY = 2, _("Quarta")
        THURSDAY = 3, _("Quinta")
        FRIDAY = 4, _("Sexta")
        SATURDAY = 5, _("Sábado")
        SUNDAY = 6, _("Domingo")

    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="working_hours")
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    weekday = models.IntegerField(_("Dia da semana"), choices=Weekday.choices)
    start_time = models.TimeField(_("Início"))
    end_time = models.TimeField(_("Fim"))

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["employee", "weekday", "start_time"], name="unique_employee_weekday_start"),
        ]

    def __str__(self):
        return f"{self.employee} - {self.get_weekday_display()} ({self.start_time} - {self.end_time})"