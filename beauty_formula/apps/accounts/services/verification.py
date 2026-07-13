
from django.conf import settings
from beauty_formula.apps.core.tokens.signing import generate_uid_token


from django.contrib.auth.tokens import default_token_generator
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode

from beauty_formula.apps.accounts.models.user import User
from beauty_formula.apps.core.exceptions import InvalidToken
from beauty_formula.apps.accounts.repositories.user_repository import activate_user
from beauty_formula.apps.accounts.selectors.user_selector import get_user_by_id


def build_verification_url(user) -> str:
    uid, token = generate_uid_token(user)
    return f"{settings.BACKEND_URL}/api/auth/verify-email/{uid}/{token}"


def build_password_reset_url(user) -> str:
    uid, token = generate_uid_token(user)
    return f"{settings.FRONTEND_URL}/redefinir-senha/{uid}/{token}"


def verify_email(uidb64: str, token: str) -> User:
    """
    Confirma o email do usuário usando uid e token.
    Retorna o usuário ativado ou levanta exceção.
    """
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = get_user_by_id(user_id=uid)

    except (User.DoesNotExist, ValueError, TypeError, OverflowError,) as e:
        raise InvalidToken(f"Link inválido ou usuário não encontrado: {e}")

    if not default_token_generator.check_token(user, token):
        raise InvalidToken("Token inválido ou expirado.")
    return activate_user(user)