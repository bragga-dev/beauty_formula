"""
Queries de Serviço — Funções para buscar e filtrar serviços.
"""
from typing import Optional, List
from uuid import UUID

from django.db.models import Q, QuerySet

from beauty_formula.apps.services.models.service import Service, DEFAULT_SERVICE_PHOTO


# ═══════════════════════════════════════════════════════════════════════════════
# Listagem Geral
# ═══════════════════════════════════════════════════════════════════════════════

def get_all_services() -> QuerySet[Service]:
    """Retorna todos os serviços, sem filtro."""
    return Service.objects.all()


def get_active_services() -> QuerySet[Service]:
    """Retorna apenas serviços ativos."""
    return Service.objects.filter(is_active=True)


def get_inactive_services() -> QuerySet[Service]:
    """Retorna apenas serviços inativos (desativados)."""
    return Service.objects.filter(is_active=False)

# ═══════════════════════════════════════════════════════════════════════════════
# Buscas Básicas por ID
# ═══════════════════════════════════════════════════════════════════════════════

def get_service_by_id(service_id: UUID) -> Optional[Service]:
    """Retorna o serviço pelo ID, ou None se não existir."""
    try:
        return Service.objects.get(id=service_id)
    except Service.DoesNotExist:
        return None


def get_services_by_ids(service_ids: List[UUID]) -> QuerySet[Service]:
    """Retorna múltiplos serviços por uma lista de IDs."""
    if not service_ids:
        return Service.objects.none()
    return Service.objects.filter(id__in=service_ids)


# ═══════════════════════════════════════════════════════════════════════════════
# Buscas por Nome
# ═══════════════════════════════════════════════════════════════════════════════

def get_service_by_name(name: str, exact: bool = True) -> Optional[Service]:
    """
    Retorna serviço pelo nome.

    Args:
        name: Nome do serviço
        exact: Se True, busca exata (case-insensitive); False busca contém
    """
    if not name:
        return None

    if exact:
        return Service.objects.filter(name__iexact=name).first()
    return Service.objects.filter(name__icontains=name).first()


def get_services_by_name_partial(name: str) -> QuerySet[Service]:
    """Retorna serviços cujo nome contenha o termo buscado."""
    if not name:
        return Service.objects.none()
    return Service.objects.filter(name__icontains=name)


def search_services(query: str) -> QuerySet[Service]:
    """Busca serviços em nome e descrição."""
    if not query:
        return Service.objects.none()
    return Service.objects.filter(
        Q(name__icontains=query) | Q(description__icontains=query)
    )


# ═══════════════════════════════════════════════════════════════════════════════
# Buscas por Funcionário
# ═══════════════════════════════════════════════════════════════════════════════

def get_services_for_employee(employee_id: UUID) -> QuerySet[Service]:
    """
    Retorna os serviços que um funcionário está apto a atender
    (via EmployeeService.active=True).
    """
    return Service.objects.filter(
        employee_assignments__employee_id=employee_id,
        employee_assignments__active=True,
    ).distinct().order_by("name")


# ═══════════════════════════════════════════════════════════════════════════════
# Buscas por Preço
# ═══════════════════════════════════════════════════════════════════════════════

def get_services_by_price_range(
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
) -> QuerySet[Service]:
    """Retorna serviços dentro de uma faixa de preço."""
    q = Q()
    if min_price is not None:
        q &= Q(price__gte=min_price)
    if max_price is not None:
        q &= Q(price__lte=max_price)

    if not q:
        return Service.objects.all()
    return Service.objects.filter(q)


def get_cheapest_services(limit: int = 5) -> QuerySet[Service]:
    """Retorna os serviços mais baratos."""
    return Service.objects.order_by("price")[:limit]


def get_most_expensive_services(limit: int = 5) -> QuerySet[Service]:
    """Retorna os serviços mais caros."""
    return Service.objects.order_by("-price")[:limit]


# ═══════════════════════════════════════════════════════════════════════════════
# Buscas por Duração
# ═══════════════════════════════════════════════════════════════════════════════

def get_services_by_duration_range(
    min_minutes: Optional[int] = None,
    max_minutes: Optional[int] = None,
) -> QuerySet[Service]:
    """Retorna serviços dentro de uma faixa de duração (em minutos)."""
    from datetime import timedelta

    q = Q()
    if min_minutes is not None:
        q &= Q(duration__gte=timedelta(minutes=min_minutes))
    if max_minutes is not None:
        q &= Q(duration__lte=timedelta(minutes=max_minutes))

    if not q:
        return Service.objects.all()
    return Service.objects.filter(q)


# ═══════════════════════════════════════════════════════════════════════════════
# Buscas por Popularidade (Agendamentos)
# ═══════════════════════════════════════════════════════════════════════════════

def get_most_booked_services(limit: int = 10) -> QuerySet[Service]:
    """Retorna os serviços mais agendados."""
    return Service.objects.order_by("-total_bookings")[:limit]


def get_services_with_no_bookings() -> QuerySet[Service]:
    """Retorna serviços que nunca foram agendados."""
    return Service.objects.filter(total_bookings=0)


# ═══════════════════════════════════════════════════════════════════════════════
# Buscas por Comissão
# ═══════════════════════════════════════════════════════════════════════════════

def get_services_by_commission_range(
    min_commission: Optional[float] = None,
    max_commission: Optional[float] = None,
) -> QuerySet[Service]:
    """Retorna serviços dentro de uma faixa de percentual de comissão."""
    q = Q()
    if min_commission is not None:
        q &= Q(commission_percentage__gte=min_commission)
    if max_commission is not None:
        q &= Q(commission_percentage__lte=max_commission)

    if not q:
        return Service.objects.all()
    return Service.objects.filter(q)


# ═══════════════════════════════════════════════════════════════════════════════
# Buscas por Imagem
# ═══════════════════════════════════════════════════════════════════════════════

def get_services_with_custom_image() -> QuerySet[Service]:
    """Retorna serviços que possuem imagem própria (não usam a imagem padrão)."""
    return Service.objects.exclude(image=DEFAULT_SERVICE_PHOTO)


def get_services_with_default_image() -> QuerySet[Service]:
    """Retorna serviços que ainda usam a imagem padrão."""
    return Service.objects.filter(image=DEFAULT_SERVICE_PHOTO)


# ═══════════════════════════════════════════════════════════════════════════════
# Filtros Avançados
# ═══════════════════════════════════════════════════════════════════════════════

def filter_services(
    search: Optional[str] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    min_duration_minutes: Optional[int] = None,
    max_duration_minutes: Optional[int] = None,
    is_active: Optional[bool] = True,
    order_by: str = "name",
) -> QuerySet[Service]:
    from datetime import timedelta

    q = Q()

    if search:
        q &= Q(name__icontains=search) | Q(description__icontains=search)

    if min_price is not None:
        q &= Q(price__gte=min_price)

    if max_price is not None:
        q &= Q(price__lte=max_price)

    if min_duration_minutes is not None:
        q &= Q(duration__gte=timedelta(minutes=min_duration_minutes))

    if max_duration_minutes is not None:
        q &= Q(duration__lte=timedelta(minutes=max_duration_minutes))

    if is_active is not None:
        q &= Q(is_active=is_active)

    qs = Service.objects.filter(q) if q else Service.objects.all()
    return qs.order_by(order_by)

# ═══════════════════════════════════════════════════════════════════════════════
# Utilitários
# ═══════════════════════════════════════════════════════════════════════════════

def validate_service_exists(service_id: UUID) -> bool:
    """Verifica se um serviço existe."""
    return Service.objects.filter(id=service_id).exists()


def validate_service_name_available(name: str, exclude_id: Optional[UUID] = None) -> bool:
    """
    Verifica se o nome do serviço está disponível (respeitando a
    UniqueConstraint do model). Usado antes de criar/renomear.
    """
    qs = Service.objects.filter(name__iexact=name)
    if exclude_id:
        qs = qs.exclude(id=exclude_id)
    return not qs.exists()


