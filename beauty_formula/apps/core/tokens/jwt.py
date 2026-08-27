"""Utilitários de emissão e revogação de JWT, reutilizáveis por qualquer app."""
from ninja_jwt.tokens import RefreshToken
from ninja_jwt.settings import api_settings
from ninja_jwt.token_blacklist.models import OutstandingToken, BlacklistedToken

from beauty_formula.apps.accounts.models.session_metadata import SessionMetadata


def make_tokens(user, user_agent: str = "") -> dict:
    refresh = RefreshToken.for_user(user)

    if user_agent:
        jti = refresh[api_settings.JTI_CLAIM]
        # Best-effort: se isso falhar por algum motivo, o login não deve
        # quebrar por causa de metadado de exibição — só a sessão fica
        # sem device legível na listagem.
        try:
            SessionMetadata.objects.create(jti=jti, user_agent=user_agent[:1000])
        except Exception:
            pass

    return {
        "access": str(refresh.access_token),
        "refresh": str(refresh),
    }


def revoke_all_tokens(user) -> None:
    for token in OutstandingToken.objects.filter(user=user):
        BlacklistedToken.objects.get_or_create(token=token)