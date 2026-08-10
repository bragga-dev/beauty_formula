"""
Helpers privados de montagem de contexto para os e-mails de agendamento.

Centraliza tudo que era repetido entre as tasks de notificação (nome de
exibição de cliente/funcionário/quem realizou uma ação, formatação de
data e duração, blocos de contexto de serviço/funcionário e montagem de
URLs do frontend), pra cada task nova só precisar montar os campos que
são específicos dela.

Nenhuma função aqui envia e-mail nem sabe qual template vai ser usado —
só monta pedaços de contexto reaproveitáveis. Quem manda o e-mail
continua sendo `send_html_email`, chamado direto pelas tasks.
"""
from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID

from django.conf import settings

from beauty_formula.apps.accounts.models.employee import Employee
from beauty_formula.apps.accounts.models.user import User
from beauty_formula.apps.accounts.selectors.client_selector import (
    get_client_by_user_id,
    get_client_full_name_display,
)
from beauty_formula.apps.accounts.selectors.employee_selector import (
    get_employee_by_user_id,
    get_employee_full_name_display,
)
from beauty_formula.apps.core.permissions.roles import is_client, is_employee
from beauty_formula.apps.services.models.scheduling import Scheduling

# ─────────────────────────────────────────────────────────────────────────
# Rotas do frontend usadas nos botões/links dos e-mails.
# Único lugar que precisa mudar se as rotas reais do app front-end forem
# diferentes dessas.
# ─────────────────────────────────────────────────────────────────────────
_CLIENT_APPOINTMENTS_PATH = "/painel/meus-agendamentos"
_EMPLOYEE_APPOINTMENTS_PATH = "/painel/meus-atendimentos"
_SALOON_PATH = "/"
_NEW_SCHEDULING_PATH = "/agendar"
_RATE_SCHEDULING_PATH_TEMPLATE = "/painel/meus-agendamentos/{scheduling_id}"


def build_frontend_url(path: str) -> str:
    """Monta uma URL absoluta do frontend a partir de um path relativo."""
    return f"{settings.FRONTEND_URL}{path}"


def client_appointments_url() -> str:
    """Link para a área 'Meus agendamentos' do cliente."""
    return build_frontend_url(_CLIENT_APPOINTMENTS_PATH)


def employee_appointments_url() -> str:
    """Link para a agenda do funcionário."""
    return build_frontend_url(_EMPLOYEE_APPOINTMENTS_PATH)


def saloon_url() -> str:
    """Link para a página do salão."""
    return build_frontend_url(_SALOON_PATH)


def new_scheduling_url() -> str:
    """Link para criar um novo agendamento."""
    return build_frontend_url(_NEW_SCHEDULING_PATH)


def rate_scheduling_url(scheduling_id: UUID) -> str:
    """Link para avaliar um agendamento concluído específico."""
    return build_frontend_url(_RATE_SCHEDULING_PATH_TEMPLATE.format(scheduling_id=scheduling_id))


# ─────────────────────────────────────────────────────────────────────────
# Nome de exibição
# ─────────────────────────────────────────────────────────────────────────

def resolve_client_display_name(user: User) -> str:
    """
    Resolve o nome de exibição do cliente a partir do `user`.
    Usa o e-mail como fallback quando o perfil de Client ainda não existe
    (ex.: e-mail disparado antes do onboarding do perfil ser concluído).
    """
    client = get_client_by_user_id(user_id=user.id)
    if client is None:
        return user.email
    return get_client_full_name_display(client)


def resolve_employee_display_name(employee: Employee) -> str:
    """Resolve o nome de exibição do funcionário (com fallback pra username/placeholder)."""
    return get_employee_full_name_display(employee)


def resolve_actor_display_name(user: Optional[User]) -> str:
    """
    Resolve um nome de exibição genérico para quem realizou uma ação (ex.:
    cancelamento) — a ação pode ter sido feita pelo cliente, por um
    funcionário ou por um admin, então o "ator" pode ser qualquer um dos
    três. Cai para "Equipe Fórmula da Beleza" quando é admin ou quando o
    usuário original não existe mais (`canceled_by` é SET_NULL).
    """
    if user is None:
        return "Equipe Fórmula da Beleza"
    if is_client(user):
        return resolve_client_display_name(user)
    if is_employee(user):
        employee = get_employee_by_user_id(user_id=user.id)
        return resolve_employee_display_name(employee) if employee else user.email
    return "Equipe Fórmula da Beleza"


# ─────────────────────────────────────────────────────────────────────────
# Formatação
# ─────────────────────────────────────────────────────────────────────────

def format_datetime_br(value: datetime) -> str:
    """Formata data/hora no padrão pt-BR usado em todos os e-mails: dd/mm/aaaa às HH:MM."""
    return value.strftime("%d/%m/%Y às %H:%M")


def duration_to_minutes(duration: timedelta) -> int:
    """Converte um timedelta de duração de serviço para minutos inteiros."""
    return int(duration.total_seconds() // 60)


# ─────────────────────────────────────────────────────────────────────────
# Blocos de contexto reutilizáveis
#
# Cada função devolve um dict pronto para `{**...}` dentro do context da
# task — assim cada e-mail só monta os campos que realmente são
# específicos dele, sem repetir a extração desses valores do model.
# ─────────────────────────────────────────────────────────────────────────

def build_service_block(scheduling: Scheduling) -> dict:
    """Campos de serviço + valores praticados no momento do agendamento."""
    return {
        "service_name": scheduling.service.name,
        "service_description": scheduling.service.description,
        "service_image": scheduling.service.image_url,
        "scheduling_service_price": scheduling.price_at_booking,
        "scheduling_service_duration": duration_to_minutes(scheduling.duration_at_booking),
    }


def build_employee_block(employee: Employee) -> dict:
    """Campos de identificação do funcionário responsável."""
    return {
        "employee_full_name": resolve_employee_display_name(employee),
        "employee_photo": employee.photo_url,
        "employee_bio": employee.bio,
    }


def build_scheduling_datetime_block(scheduling: Scheduling) -> dict:
    """Campos de data/horário do agendamento, já formatados em pt-BR, e status atual."""
    return {
        "scheduling_service_time": format_datetime_br(scheduling.scheduled_time),
        "scheduling_service_status": scheduling.get_status_display(),
    }