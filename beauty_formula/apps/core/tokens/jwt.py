
"""Utilitários de emissão e revogação de JWT, reutilizáveis por qualquer app."""
from ninja_jwt.tokens import RefreshToken
from ninja_jwt.token_blacklist.models import OutstandingToken, BlacklistedToken


def make_tokens(user) -> dict:
    refresh = RefreshToken.for_user(user)
    return {
        "access": str(refresh.access_token),
        "refresh": str(refresh),
    }


def revoke_all_tokens(user) -> None:
    for token in OutstandingToken.objects.filter(user=user):
        BlacklistedToken.objects.get_or_create(token=token)