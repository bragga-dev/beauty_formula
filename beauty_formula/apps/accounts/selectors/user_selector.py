"""
User Selectors — queries de leitura para User.
Nenhuma escrita acontece aqui.
"""
import uuid
from datetime import datetime
from typing import Optional
from django.db.models import QuerySet, Q
from beauty_formula.apps.accounts.models.user import User


# ── Busca individual ──────────────────────────────────────────────────────────

def get_user_by_id(user_id: uuid.UUID) -> Optional[User]:
    """Busca usuário por ID."""
    return User.objects.filter(pk=user_id).first()


def get_user_by_email(email: str) -> Optional[User]:
    """Busca usuário por e-mail (case insensitive)."""
    return User.objects.filter(email__iexact=email).first()

# ── Verificações de existência ────────────────────────────────────────────────

def email_exists(email: str, exclude_id: Optional[uuid.UUID] = None) -> bool:
    """
    Verifica se e-mail já está em uso.
    Passa exclude_id para ignorar o próprio usuário em updates.
    """
    qs = User.objects.filter(email__iexact=email)
    if exclude_id:
        qs = qs.exclude(pk=exclude_id)
    return qs.exists()


def user_exists(user_id: uuid.UUID) -> bool:
    """Verifica se usuário existe."""
    return User.objects.filter(pk=user_id).exists()


# ── Listagens ─────────────────────────────────────────────────────────────────

def get_all_users() -> QuerySet[User]:
    """Retorna todos os usuários."""
    return User.objects.all()


def get_active_users() -> QuerySet[User]:
    """Retorna usuários ativos."""
    return User.objects.filter(is_active=True)


def get_inactive_users() -> QuerySet[User]:
    """Retorna usuários inativados."""
    return User.objects.filter(is_active=False)


def get_users_by_role(role: str) -> QuerySet[User]:
    """Retorna usuários por role. Use as constantes: ROLE_CLIENT, ROLE_EMPLOYEE, ROLE_ADMIN."""
    return User.objects.filter(role=role)


def get_trusty_users() -> QuerySet[User]:
    """Retorna usuários marcados como confiáveis."""
    return User.objects.filter(is_trusty=True)


def get_staff_users() -> QuerySet[User]:
    """Retorna usuários com acesso ao admin."""
    return User.objects.filter(is_staff=True)

def get_user_confirmed_by_role(user_id: uuid.UUID, role: str) -> Optional[User]:
    """Retorna usuário confirmado pelo ID e Role"""
    return User.objects.filter(pk=user_id, role=role, is_trusty=True, is_active=True).first()

# ── Exclusões ─────────────────────────────────────────────────────────────────

def get_users_excluding_id(user_id: uuid.UUID) -> QuerySet[User]:
    """Retorna todos os usuários exceto o informado."""
    return User.objects.exclude(pk=user_id)


def get_users_excluding_role(role: str) -> QuerySet[User]:
    """Retorna usuários que não possuem o role informado."""
    return User.objects.exclude(role=role)


# ── Ordenação ─────────────────────────────────────────────────────────────────

def get_users_ordered_by_date(descending: bool = True) -> QuerySet[User]:
    """Retorna usuários ordenados por data de cadastro."""
    order = "-date_joined" if descending else "date_joined"
    return User.objects.order_by(order)


# ── Combinados ────────────────────────────────────────────────────────────────

def get_active_users_by_role(role: str) -> QuerySet[User]:
    """Retorna usuários ativos de um role específico."""
    return User.objects.filter(is_active=True, role=role)


def get_user_with_related(user_id: uuid.UUID) -> Optional[User]:
    """
    Busca usuário com select_related para employee_profile ou client_profile.
    Evita N+1 quando você vai acessar user.client_profile ou user.employee_profile logo depois.
    """
    return (
        User.objects
        .select_related("employee_profile", "client_profile")
        .filter(pk=user_id)
        .first()
    )


# ── Search ────────────────────────────────────────────────────────────────────

def search_users(query: str):
    query = query.strip()

    if not query:
        return User.objects.none()

    return User.objects.filter(
        Q(email__icontains=query) |

        Q(client__first_name__icontains=query) |
        Q(client__last_name__icontains=query) |
        Q(client__username__icontains=query) |
        Q(client__gender__icontains=query) |

        Q(employee__first_name__icontains=query) |
        Q(employee__last_name__icontains=query) |
        Q(employee__username__icontains=query) |
        Q(employee__gender__icontains=query) |
        Q(employee__bio__icontains=query) 
    ).distinct()

def search_users_by_role_and_status(role: str, is_active: bool) -> QuerySet[User]:
    """
    Filtra usuários por role e status.
    Ex: todos os clien ativos, todas as funcionários inativas.
    """
    return User.objects.filter(role=role, is_active=is_active)


def get_users_by_date_range(start: datetime, end: datetime) -> QuerySet[User]:
    """Usuários cadastrados num período — útil pra relatórios."""
    return User.objects.filter(date_joined__date__range=(start, end))