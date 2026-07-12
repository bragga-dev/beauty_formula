"""
Auth Services — autenticação, login, logout, refresh token.
"""
from django.contrib.auth import authenticate
from ninja_jwt.tokens import RefreshToken
from ninja_jwt.token_blacklist.models import OutstandingToken, BlacklistedToken
from beauty_formula.apps.core.tokens.jwt import make_tokens, revoke_all_tokens
from beauty_formula.apps.core.exceptions import (
    InvalidCredentials,
    InvalidToken,
    InvalidPassword,
    EmailNotVerified,
)


from django.contrib.auth.tokens import default_token_generator
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from beauty_formula.apps.accounts.models.user import User
from beauty_formula.apps.accounts.selectors.user_selector import get_user_by_email
from beauty_formula.apps.core.exceptions.auth import InvalidToken



def login_user(email: str, password: str) -> dict:
    user = authenticate(username=email, password=password)

    if not user:
        # Verifica se existe mas está inativo (email não confirmado)
        try:
            inactive_user = User.objects.get(email=email)
            if not inactive_user.is_active and inactive_user.check_password(password):
                raise EmailNotVerified()
        except User.DoesNotExist:
            pass
        raise InvalidCredentials()

    return make_tokens(user)


def logout_user(refresh_token: str) -> None:
    """Blacklista o refresh token (requer ninja_jwt.token_blacklist)."""
    try:
        token = RefreshToken(refresh_token)
        token.blacklist()
    except Exception:
        raise InvalidToken()


def refresh_access_token(refresh_token: str) -> dict:
    try:
        token = RefreshToken(refresh_token)
        return {"access": str(token.access_token)}
    except Exception:
        raise InvalidToken()


def change_password(user: User, old_password: str, new_password: str) -> dict:
    """
    Troca a senha e invalida todos os refresh tokens ativos do usuário.
    Retorna um novo par de tokens para manter a sessão ativa.
    """
    if not user.check_password(old_password):
        raise InvalidPassword()

    user.set_password(new_password)
    user.save(update_fields=["password"])

    revoke_all_tokens(user)
    return make_tokens(user)


def request_password_reset(email: str) -> None:
    """
    Sempre retorna sem erro mesmo que o e-mail não exista
    (evita enumeração de usuários).
    """
    user = get_user_by_email(email)
    if not user:
        return

    from beauty_formula.apps.accounts.tasks.password_reset import send_password_reset_email
    uid = urlsafe_base64_encode(force_bytes(user.pk)).rstrip("=")
    token = default_token_generator.make_token(user)
    send_password_reset_email.delay(user.pk, uid, token)


def confirm_password_reset(uidb64: str, token: str, new_password: str) -> None:
    try:
        padding = (4 - len(uidb64) % 4) % 4
        uid = force_str(urlsafe_base64_decode(uidb64 + "=" * padding))
        user = User.objects.get(pk=uid)
    except (User.DoesNotExist, ValueError, TypeError):
        raise InvalidToken()

    if not default_token_generator.check_token(user, token):
        raise InvalidToken()

    user.set_password(new_password)
    user.save(update_fields=["password"])