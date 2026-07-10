



import uuid


from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _
from beauty_formula.apps.accounts.models.user import User
from beauty_formula.apps.services.models.service import Service
from django.utils import timezone




class Scheduling(models.Model):
    class SchedulingStatus(models.TextChoices):
        PENDING = "pending", _("Pendente")
        CONFIRMED = "confirmed", _("Confirmado")
        IN_PROGRESS = "in_progress", _("Em andamento")  
        COMPLETED = "completed", _("Concluído")
        CANCELED = "canceled", _("Cancelado")
        NO_SHOW = "no_show", _("Não compareceu")  
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    service = models.ForeignKey(Service, on_delete=models.PROTECT, related_name="schedulings")
    client = models.ForeignKey('accounts.Client', on_delete=models.PROTECT, related_name="schedulings")
    employee = models.ForeignKey('accounts.Employee', on_delete=models.PROTECT, related_name="schedulings")
    scheduled_time = models.DateTimeField(_("Horário agendado"))
    status = models.CharField(_("Status"), max_length=20, choices=SchedulingStatus.choices, default=SchedulingStatus.PENDING, db_index=True)
    price_at_booking = models.DecimalField(_("Preço no momento do agendamento"), max_digits=10, decimal_places=2, editable=False)
    duration_at_booking = models.DurationField(_("Duração no momento do agendamento"), editable=False)    
    notes = models.TextField(_("Observações"), blank=True, null=True)
    canceled_at = models.DateTimeField(_("Cancelado em"), blank=True, null=True)
    canceled_reason = models.CharField(_("Motivo do cancelamento"), max_length=255, blank=True, null=True)
    canceled_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="canceled_schedulings")
    rated_at = models.DateTimeField(_("Avaliado em"), blank=True, null=True)
    is_active = models.BooleanField(_("Ativo"), default=True, help_text=_("Desative em vez de deletar para não quebrar agendamentos antigos."))
    created_at = models.DateTimeField(_("Criado em"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Atualizado em"), auto_now=True)
    
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
        return f"#{self.id[:8]} - {self.service.name} - {self.client} - {self.scheduled_time.strftime('%d/%m/%Y %H:%M')}"
    
    def clean(self):
        """Validações do agendamento"""
        
        # 1. Validação de conflito
        if self.duration_at_booking:
            end_time = self.scheduled_time + self.duration_at_booking
            
            conflicts = Scheduling.objects.filter(
                employee=self.employee,
                status__in=[
                    self.SchedulingStatus.PENDING, 
                    self.SchedulingStatus.CONFIRMED,
                    self.SchedulingStatus.IN_PROGRESS
                ],
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
        if not self.pk:     
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
        """Verifica se o cliente pode cancelar"""
        if self.status in [self.SchedulingStatus.COMPLETED, self.SchedulingStatus.CANCELED]:
            return False
        
        # Permite cancelar até 2h antes
        hours_diff = (self.scheduled_time - timezone.now()).total_seconds() / 3600
        return hours_diff >= 2
    
    @property
    def can_be_canceled_by_admin(self):
        """Verifica se o admin pode cancelar"""
        return self.status not in [self.SchedulingStatus.COMPLETED, self.SchedulingStatus.CANCELED]
    
    # ========== MÉTODOS ==========
    def cancel(self, reason: str, canceled_by: User):
        """Cancela o agendamento"""
        self.status = self.SchedulingStatus.CANCELED
        self.canceled_at = timezone.now()
        self.canceled_reason = reason
        self.canceled_by = canceled_by
        self.is_active = False
        self.save()
    
    def confirm(self):
        """Confirma o agendamento"""
        if self.status == self.SchedulingStatus.PENDING:
            self.status = self.SchedulingStatus.CONFIRMED
            self.save()
    
    def start(self):
        """Inicia o atendimento"""
        if self.status == self.SchedulingStatus.CONFIRMED:
            self.status = self.SchedulingStatus.IN_PROGRESS
            self.save()
    
    def complete(self):
        """Conclui o atendimento"""
        if self.status == self.SchedulingStatus.IN_PROGRESS:
            self.status = self.SchedulingStatus.COMPLETED
            self.save()
    
    def mark_as_no_show(self):
        """Marca como não compareceu"""
        if self.status in [self.SchedulingStatus.PENDING, self.SchedulingStatus.CONFIRMED]:
            self.status = self.SchedulingStatus.NO_SHOW
            self.canceled_at = timezone.now()
            self.canceled_reason = "Cliente não compareceu"
            self.is_active = False
            self.save()