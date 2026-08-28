"""
Traduz um User-Agent bruto (HTTP header) pra um label curto e legível
("Chrome no Windows", "Safari no iPhone") pra exibir na lista de sessões.

De propósito, isso NÃO mora no model `SessionMetadata` — o model só
guarda a string bruta. Esse parsing é puramente de apresentação:
regex simples e best-effort, sem pretensão de precisão forense. Se um
dia vier a precisar de detecção robusta (bot, versão exata, etc.), essa
é a função a trocar por uma lib — nenhuma migration de dado necessária,
porque o bruto continua guardado.
"""
import re
from typing import Optional


_BROWSER_PATTERNS = [
    (re.compile(r"Edg/", re.I), "Edge"),
    (re.compile(r"OPR/|Opera", re.I), "Opera"),
    (re.compile(r"Chrome/", re.I), "Chrome"),
    (re.compile(r"CriOS/", re.I), "Chrome"),
    (re.compile(r"FxiOS/", re.I), "Firefox"),
    (re.compile(r"Firefox/", re.I), "Firefox"),
    (re.compile(r"Version/.*Safari/", re.I), "Safari"),
    (re.compile(r"Safari/", re.I), "Safari"),
]

_OS_PATTERNS = [
    (re.compile(r"iPhone", re.I), "iPhone"),
    (re.compile(r"iPad", re.I), "iPad"),
    (re.compile(r"Android", re.I), "Android"),
    (re.compile(r"Windows", re.I), "Windows"),
    (re.compile(r"Mac OS X|Macintosh", re.I), "macOS"),
    (re.compile(r"Linux", re.I), "Linux"),
]


def describe_user_agent(user_agent: str) -> Optional[str]:
    """
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) ... Chrome/128.0 ..."
    -> "Chrome no Windows"

    Retorna None se o user-agent estiver vazio (sessão antiga, criada
    antes desse rastreamento existir, ou requisição sem header) — o
    front trata `None` mostrando um label genérico de fallback.
    """
    if not user_agent:
        return None

    browser = next((label for pattern, label in _BROWSER_PATTERNS if pattern.search(user_agent)), None)
    os_name = next((label for pattern, label in _OS_PATTERNS if pattern.search(user_agent)), None)

    if browser and os_name:
        return f"{browser} no {os_name}"
    if browser:
        return browser
    if os_name:
        return os_name
    return None