import uuid
from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class ConsentLog(models.Model):
    """
    Trilha de auditoria de consentimentos (LGPD art. 8º, §2º: o controlador
    tem o ônus de provar o consentimento). Só recebe INSERTs.

    `user` usa SET_NULL e `user_ref` guarda o UUID: se a conta for excluída,
    o registro de prova permanece sem apontar para dados pessoais da conta.
    """

    class Document(models.TextChoices):
        TERMS = "terms", _("Termos de Uso")
        PRIVACY = "privacy", _("Política de Privacidade")
        MARKETING = "marketing", _("Comunicações promocionais")

    class Action(models.TextChoices):
        ACCEPTED = "accepted", _("Aceito")
        REVOKED = "revoked", _("Revogado")

    class Source(models.TextChoices):
        SIGNUP = "signup", _("Cadastro")
        GOOGLE = "google", _("Cadastro via Google")
        RE_ACCEPT = "re_accept", _("Novo aceite")
        SETTINGS = "settings", _("Configurações da conta")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="consent_logs")
    user_ref = models.UUIDField(_("ID do usuário"), db_index=True)
    document = models.CharField(_("Documento"), max_length=20, choices=Document.choices)
    version = models.CharField(_("Versão"), max_length=20, blank=True, default="")
    action = models.CharField(_("Ação"), max_length=20, choices=Action.choices)
    source = models.CharField(_("Origem"), max_length=20, choices=Source.choices)
    ip_address = models.GenericIPAddressField(_("IP"), null=True, blank=True)
    user_agent = models.CharField(_("User agent"), max_length=255, blank=True, default="")
    created_at = models.DateTimeField(_("Registrado em"), auto_now_add=True)

    class Meta:
        verbose_name = _("Registro de consentimento")
        verbose_name_plural = _("Registros de consentimento")
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["user_ref", "-created_at"])]

    def __str__(self):
        return f"{self.document} {self.action} v{self.version} ({self.user_ref})"