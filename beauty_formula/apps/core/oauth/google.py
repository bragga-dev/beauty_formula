"""
Validação de ID Token do Google (Google Identity Services / Sign in with Google).

O frontend usa o Google Identity Services para autenticar o usuário e recebe
de volta um JWT assinado pelo Google (o "credential"). Esse token é enviado
ao backend, que o valida aqui — sem nunca confiar em dados enviados "soltos"
pelo cliente (nome, email, etc. sempre vêm de dentro do token verificado).
"""
from google.auth.exceptions import GoogleAuthError
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as google_id_token

from django.conf import settings

from beauty_formula.apps.core.exceptions.auth import InvalidGoogleToken

_VALID_ISSUERS = {"accounts.google.com", "https://accounts.google.com"}

_google_request = google_requests.Request()


def verify_google_id_token(token: str) -> dict:
    """
    Valida assinatura, expiração, issuer e audience (client_id) do id_token.
    Retorna os claims do Google em caso de sucesso.

    Levanta InvalidGoogleToken se o token for inválido, expirado, ou não
    tiver sido emitido para este client_id.
    """
    if not token or not token.strip():
        raise InvalidGoogleToken("Token do Google não informado.")

    try:
        claims = google_id_token.verify_oauth2_token(
            token,
            _google_request,
            settings.GOOGLE_CLIENT_ID,
        )
    except (ValueError, GoogleAuthError):
        raise InvalidGoogleToken()

    if claims.get("iss") not in _VALID_ISSUERS:
        raise InvalidGoogleToken()

    return claims