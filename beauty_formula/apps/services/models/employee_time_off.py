import uuid
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _
from beauty_formula.apps.services.models.employee_works_hours import EmployeeWorkingHours
from beauty_formula.apps.core.constants.block_type import BlockType


class EmployeeTimeOff(models.Model):
    """Modelo que representa folgas, férias e bloqueios de horário de um funcionário."""

    class BlockModality(models.TextChoices):
        """
        Discriminador explícito de modalidade — quem decide o valor é o
        endpoint chamado (recorrente ou pontual), não uma inferência a
        partir de quais campos vieram preenchidos. Isso é o que permite
        ter duas rotas exclusivas de criação em vez de uma só genérica.
        """
        RECURRING = "recurring", _("Bloqueio Recorrente")
        PUNCTUAL = "punctual", _("Bloqueio Pontual")

    employee = models.ForeignKey("accounts.Employee", on_delete=models.CASCADE, related_name="time_off")
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    block_type = models.CharField(_("Tipo"), max_length=20, choices=BlockType.CHOICES, default=BlockType.OTHER)
    block_modality = models.CharField(_("Modalidade do Bloqueio"), max_length=20, choices=BlockModality.choices, default=BlockModality.RECURRING,)
    weekday = models.IntegerField(_("Dia da semana"), choices=EmployeeWorkingHours.Weekday.choices, null=True, blank=True)
    start_time = models.TimeField(_("Início"), null=True, blank=True)
    end_time = models.TimeField(_("Fim"), null=True, blank=True)
    start_datetime = models.DateTimeField(_("Início"), null=True, blank=True)
    end_datetime = models.DateTimeField(_("Fim"), null=True, blank=True)
    is_active = models.BooleanField(_("Ativo"), default=True, help_text=_("Usado pela expiração automática de bloqueios pontuais: a task do "
            "Celery marca como False (soft delete) 1 minuto após end_datetime, ""em vez de excluir o registro."
        ),
    )

    @property
    def is_recurring(self) -> bool:
        return self.block_modality == self.BlockModality.RECURRING

    @property
    def is_punctual(self) -> bool:
        return self.block_modality == self.BlockModality.PUNCTUAL

    def clean(self):
        if self.block_modality == self.BlockModality.RECURRING:
            self._validate_recurring()
        elif self.block_modality == self.BlockModality.PUNCTUAL:
            self._validate_punctual()
        else:
            raise ValidationError(_("Modalidade de bloqueio desconhecida."))

    def _validate_recurring(self):
        """
        Nota: usa `is None`, nunca `if self.weekday` — weekday=0 é
        Segunda-feira, e 0 é falsy em Python. Um `if self.weekday` teria
        deixado passar batido qualquer bloqueio recorrente de segunda.
        """
        if self.weekday is None or self.start_time is None or self.end_time is None:
            raise ValidationError(_("Bloqueio recorrente exige weekday, start_time e end_time."))
        if self.start_time >= self.end_time:
            raise ValidationError(_("Bloqueio recorrente exige start_time < end_time."))
        if self.start_datetime is not None or self.end_datetime is not None:
            raise ValidationError(_("Bloqueio recorrente não deve preencher start_datetime/end_datetime."))

    def _validate_punctual(self):
        if self.start_datetime is None or self.end_datetime is None:
            raise ValidationError(_("Bloqueio pontual exige start_datetime e end_datetime."))
        if self.end_datetime <= self.start_datetime:
            raise ValidationError(_("end_datetime deve ser depois de start_datetime."))
        if self.weekday is not None or self.start_time is not None or self.end_time is not None:
            raise ValidationError(_("Bloqueio pontual não deve preencher weekday/start_time/end_time."))

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