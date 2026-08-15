"""
Cookie do refresh token.

O access token (curta duração) continua indo no corpo da resposta JSON —
o frontend guarda em memória, nunca em localStorage. O refresh token (o que
dá acesso persistente, dias de validade) sai do corpo da resposta e vai só
num cookie httpOnly: JavaScript não consegue ler (`document.cookie` não
mostra), então um XSS no front não consegue mais roubar a sessão inteira,
só o access token que já está em memória (e que expira em minutos).

O cookie é restrito a `path=/api/auth` — só é enviado pra esses endpoints
(login, refresh, logout, register etc.), não pra API inteira.
"""
from django.conf import settings
from django.http import HttpResponse
from ninja_jwt.settings import api_settings

REFRESH_COOKIE_NAME = "fb_refresh_token"
REFRESH_COOKIE_PATH = "/api/auth"


def set_refresh_cookie(response: HttpResponse, refresh_token: str) -> None:
    response.set_cookie(
        REFRESH_COOKIE_NAME,
        refresh_token,
        max_age=int(api_settings.REFRESH_TOKEN_LIFETIME.total_seconds()),
        path=REFRESH_COOKIE_PATH,
        httponly=True,
        # Em dev (HTTP puro / ngrok sem TLS local) o cookie Secure seria
        # descartado pelo browser. Em prod (DEBUG=False, sempre HTTPS por
        # causa do SECURE_SSL_REDIRECT) fica Secure de verdade.
        secure=not settings.DEBUG,
        samesite="Lax",
    )


def clear_refresh_cookie(response: HttpResponse) -> None:
    response.delete_cookie(REFRESH_COOKIE_NAME, path=REFRESH_COOKIE_PATH)