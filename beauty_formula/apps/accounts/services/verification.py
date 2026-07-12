
from django.conf import settings
from beauty_formula.apps.core.tokens.signing import generate_uid_token


def build_verification_url(user) -> str:
    uid, token = generate_uid_token(user)
    return f"{settings.BACKEND_URL}/api/users/verify-email/{uid}/{token}"


def build_password_reset_url(user) -> str:
    uid, token = generate_uid_token(user)
    return f"{settings.FRONTEND_URL}/redefinir-senha/{uid}/{token}"