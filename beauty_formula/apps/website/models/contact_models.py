import uuid
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinLengthValidator, MaxLengthValidator, EmailValidator

class Contact(models.Model):
    class ContactSubject(models.TextChoices):
            APPOINMENT = "appointment", _("Agendamento")
            QUESTION = "question", _("Dúvida")
            COMPLIMENT = "compliment", _("Elogio")
            COMPLAINT = "complaint", _("Reclamação")
            OTHER = "other", _("Outro")

    class ContactStatus(models.TextChoices):
        PENDING = "pending", _("Pendente")
        IN_PROGRESS = "in_progress", _("Em andamento")
        RESOLVED = "resolved", _("Resolvido")
        ARCHIVED = "archived", _("Arquivado")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    full_name = models.CharField(_("Nome completo"), max_length=255, blank=False, null=False)
    subject = models.TextField(_("Assunto"), blank=False, null=False, choices=ContactSubject.choices, default=ContactSubject.OTHER)
    message = models.TextField(_("Mensagem"), blank=False, null=False)
    email = models.EmailField(_("E-mail"), max_length=255, blank=False, null=False, validators=[EmailValidator(message=_("Digite um e-mail válido"))])
    phone = models.CharField(_("Telefone"), max_length=20, blank=False, null=False)
    status = models.TextField(_("Status"), blank=False, null=False, choices=ContactStatus.choices, default=ContactStatus.PENDING)
    created_at = models.DateTimeField(_("Criado em"), auto_now_add=True)

    def __str__(self):
        return self.full_name


    class Meta:
        verbose_name = _("Contato")
        verbose_name_plural = _("Contatos")
        indexes = [
            models.Index(fields=["full_name"]),
            models.Index(fields=["status"]),
            models.Index(fields=["created_at"]),
            models.Index(fields=["email"]),
            
        ]
        ordering = ["full_name"]
        constraints = [
            models.UniqueConstraint(fields=["full_name"], name="unique_contact_name")
        ]