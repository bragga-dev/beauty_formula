"""Dados da requisição usados em trilhas de auditoria (IP e user agent)."""
from typing import Optional


def get_client_ip(request) -> Optional[str]:
    """
    IP real do cliente. Atrás do Nginx, REMOTE_ADDR é o proxy: o Nginx envia o
    IP real em X-Real-IP (sobrescrevendo o que o cliente mandar).
    """
    return request.META.get("HTTP_X_REAL_IP") or request.META.get("REMOTE_ADDR") or None


def get_user_agent(request) -> str:
    return (request.headers.get("User-Agent", "") or "")[:255]