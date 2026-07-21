# core/tokens/signing.py
from django.contrib.auth.tokens import default_token_generator
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode


def generate_uid_token(user) -> tuple[str, str]:
    """Gera um par (uid, token) assinado de uso único para um usuário."""
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    return uid, token