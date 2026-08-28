import uuid


from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _
from beauty_formula.apps.accounts.models.user import User
from beauty_formula.apps.core.exceptions.service_exception import InvalidSchedulingStatusTransition
from beauty_formula.apps.services.models.service import Service
from django.utils import timezone


class Scheduling(models.Model):
    class SchedulingStatus(models.TextChoices):
        CREATED = "created", _("Criado")
        CONFIRMED = "confirmed", _("Confirmado")
        COMPLETED = "completed", _("Concluído")
        CANCELED = "canceled", _("Cancelado")
        NO_SHOW = "no_show", _("Não compareceu")
        RESCHEDULED = "rescheduled", _("Reagendado")

    ALLOWED_TRANSITIONS = \
    {
        SchedulingStatus.CREATED: {SchedulingStatus.CONFIRMED, SchedulingStatus.CANCELED},

        SchedulingStatus.CONFIRMED: 
        {
            SchedulingStatus.COMPLETED,
            SchedulingStatus.CANCELED,
            SchedulingStatus.NO_SHOW,
            SchedulingStatus.RESCHEDULED,
        },
        SchedulingStatus.COMPLETED: set(),
        SchedulingStatus.CANCELED: set(),
        SchedulingStatus.NO_SHOW: set(),
        SchedulingStatus.RESCHEDULED: set(),
    }

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    service = models.ForeignKey(Service, on_delete=models.PROTECT, related_name="service_schedulings")
    client = models.ForeignKey('accounts.Client', on_delete=models.PROTECT, related_name="client_schedulings")
    employee = models.ForeignKey('accounts.Employee', on_delete=models.PROTECT, related_name="employee_schedulings")
    scheduled_time = models.DateTimeField(_("Horário agendado"))
    status = models.CharField(_("Status"), max_length=20, choices=SchedulingStatus.choices, default=SchedulingStatus.CREATED, db_index=True)
    price_at_booking = models.DecimalField(_("Preço no momento do agendamento"), max_digits=10, decimal_places=2, editable=False)
    duration_at_booking = models.DurationField(_("Duração no momento do agendamento"), editable=False)
    notes = models.TextField(_("Observações"), blank=True, null=True)
    canceled_at = models.DateTimeField(_("Cancelado em"), blank=True, null=True)
    canceled_reason = models.CharField(_("Motivo do cancelamento"), max_length=255, blank=True, null=True)
    canceled_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="canceled_schedulings")
    rated_at = models.DateTimeField(_("Avaliado em"), blank=True, null=True)
    completed_at = models.DateTimeField(
        _("Concluído em"),
        blank=True,
        null=True,
        help_text=_(
            "Momento exato em que o status virou COMPLETED. Diferente de "
            "`updated_at` (que muda a qualquer edição), este campo só é "
            "preenchido uma vez, dentro de complete() — é a base usada pra "
            "calcular a competência (mês) da comissão gerada a partir daqui."
        ),
    )
    rescheduled_to = models.OneToOneField(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="rescheduled_from",
        verbose_name=_("Reagendado para"),
        help_text=_("Novo agendamento criado a partir do reagendamento deste registro."),
    )
    is_active = models.BooleanField(_("Ativo"), default=True, help_text=_("Desative em vez de deletar para não quebrar agendamentos antigos."))
    created_at = models.DateTimeField(_("Criado em"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Atualizado em"), auto_now=True)
    reminder_sent_at = models.DateTimeField(_("Lembrete enviado em"), null=True, blank=True)
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
            models.Index(fields=["status", "scheduled_time"]),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(
                    models.Q(status__in=['canceled', 'no_show'], canceled_at__isnull=False) |
                    models.Q(~models.Q(status__in=['canceled', 'no_show']), canceled_at__isnull=True)
                ),
                name="canceled_status_requires_canceled_at"
            )
        ]

    def __str__(self):
        return f"#{self.id} - {self.service.name} - {self.client} - {self.scheduled_time.strftime('%d/%m/%Y %H:%M')}"

    def clean(self):
        """Validações do agendamento"""

        if self.duration_at_booking:
            end_time = self.scheduled_time + self.duration_at_booking

            conflicts = Scheduling.objects.filter(
                employee=self.employee,
                status=self.SchedulingStatus.CONFIRMED,
                scheduled_time__lt=end_time,
                is_active=True
            ).exclude(pk=self.pk)

            for s in conflicts:
                s_end = s.scheduled_time + s.duration_at_booking
                if s_end > self.scheduled_time:
                    raise ValidationError(
                        _("Funcionário já possui agendamento nesse horário: %(time)s - %(service)s"),
                        params={
                            'time': s.scheduled_time.strftime('%H:%M'),
                            'service': s.service.name
                        }
                    )

    def save(self, *args, **kwargs):
        if self._state.adding:
            self.price_at_booking = self.service.price
            self.duration_at_booking = self.service.duration

        self.full_clean()
        super().save(*args, **kwargs)

    # ========== PROPRIEDADES ==========
    @property
    def end_time(self):
        """Retorna o horário de término do agendamento"""
        return self.scheduled_time + self.duration_at_booking

    @property
    def is_past(self):
        """Verifica se o agendamento já passou"""
        return self.end_time < timezone.now()

    @property
    def is_upcoming(self):
        """Verifica se o agendamento é futuro"""
        return self.scheduled_time > timezone.now()

    @property
    def is_today(self):
        """Verifica se o agendamento é hoje"""
        return self.scheduled_time.date() == timezone.now().date()

    @property
    def can_be_canceled_by_client(self):
        """
        Verifica se o cliente pode cancelar.

        Uma reserva CREATED (ainda não paga) pode ser cancelada a
        qualquer momento — a janela mínima de 2h só se aplica a partir
        do momento em que o agendamento é efetivamente CONFIRMED, pois
        antes disso o horário nem está de fato ocupado (ver BUSY_STATUSES
        em scheduling_selector).
        """
        if self.status == self.SchedulingStatus.CREATED:
            return True

        if self.status != self.SchedulingStatus.CONFIRMED:
            return False

        hours_diff = (self.scheduled_time - timezone.now()).total_seconds() / 3600
        return hours_diff >= 2

    @property
    def can_be_canceled_by_admin(self):
        """Verifica se o admin/funcionário pode cancelar"""
        return self.status in {self.SchedulingStatus.CREATED, self.SchedulingStatus.CONFIRMED}

    @property
    def can_be_rescheduled(self):
        """Verifica se o agendamento pode ser reagendado"""
        return self.status == self.SchedulingStatus.CONFIRMED

    # ========== MÁQUINA DE ESTADOS ==========
    def can_transition_to(self, target_status: str) -> bool:
        """Verifica se a transição do status atual para `target_status` é permitida."""
        return target_status in self.ALLOWED_TRANSITIONS.get(self.status, set())

    def _ensure_transition_allowed(self, target_status: str) -> None:
        if not self.can_transition_to(target_status):
            raise InvalidSchedulingStatusTransition(
                _("Não é possível mudar de %(current)s para %(target)s.") % {
                    "current": self.get_status_display(),
                    "target": dict(self.SchedulingStatus.choices).get(target_status, target_status),
                }
            )

    # ========== MÉTODOS ==========
    def cancel(self, reason: str, canceled_by: User):
        """Cancela o agendamento"""
        self._ensure_transition_allowed(self.SchedulingStatus.CANCELED)
        self.status = self.SchedulingStatus.CANCELED
        self.canceled_at = timezone.now()
        self.canceled_reason = reason
        self.canceled_by = canceled_by
        self.is_active = False
        self.save()

    def confirm(self):
        """Marca uma agendamendo como Confirmado"""
        self._ensure_transition_allowed(self.SchedulingStatus.CONFIRMED)
        self.status = self.SchedulingStatus.CONFIRMED
        self.save()                

    def complete(self):
        """Conclui o atendimento"""
        self._ensure_transition_allowed(self.SchedulingStatus.COMPLETED)
        self.status = self.SchedulingStatus.COMPLETED
        self.completed_at = timezone.now()
        self.save()

    def mark_as_no_show(self, reason: str = "Cliente não compareceu"):
        """
        Marca como não compareceu. `reason` tem um padrão pro caso comum
        (funcionário marcando manualmente), mas pode ser sobrescrito —
        usado, por exemplo, pela task `close_overdue_schedulings`, que
        fecha agendamentos vencidos automaticamente com um motivo próprio.
        """
        self._ensure_transition_allowed(self.SchedulingStatus.NO_SHOW)
        self.status = self.SchedulingStatus.NO_SHOW
        self.canceled_at = timezone.now()
        self.canceled_reason = reason
        self.is_active = False
        self.save()

    def mark_as_rescheduled(self, new_scheduling: "Scheduling"):
        """
        Marca este agendamento como reagendado, vinculando-o ao novo
        registro criado em seu lugar. Não altera a data deste registro —
        preserva o histórico original para auditoria e relatórios.
        """
        self._ensure_transition_allowed(self.SchedulingStatus.RESCHEDULED)
        self.status = self.SchedulingStatus.RESCHEDULED
        self.rescheduled_to = new_scheduling
        self.is_active = False
        self.save()