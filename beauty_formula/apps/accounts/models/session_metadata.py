from django.db import models
from django.utils.translation import gettext_lazy as _


class SessionMetadata(models.Model):
    """
    Metadado de sessão (login) que o `OutstandingToken` da lib
    `ninja_jwt.token_blacklist` não guarda — é model de terceiro, não
    estendemos ele diretamente.

    Guarda só o User-Agent BRUTO enviado no momento do login. Nenhuma
    lógica de identificação de dispositivo/navegador mora aqui — isso é
    responsabilidade da camada de serviço/apresentação (ver
    `beauty_formula.apps.accounts.services.session_presenter`), pra não
    prender o dado bruto a uma lista de regex que fica desatualizada.

    Casado ao token via `jti` (chave única do próprio OutstandingToken),
    não por FK direta — assim não dependemos do ciclo de vida do model
    de terceiro nem arriscamos migration cruzada de app.
    """
    jti = models.CharField(_("JTI do token"), max_length=255, unique=True, db_index=True)
    user_agent = models.TextField(_("User-Agent"), blank=True, default="")
    created_at = models.DateTimeField(_("Criado em"), auto_now_add=True)

    class Meta:
        verbose_name = _("Metadado de sessão")
        verbose_name_plural = _("Metadados de sessão")

    def __str__(self):
        return f"Sessão {self.jti[:8]}…"