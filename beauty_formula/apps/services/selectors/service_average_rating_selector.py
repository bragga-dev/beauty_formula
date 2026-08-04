"""
Queries de ServiceAverageRating — agregado de leitura (cache) com a média
de avaliações por serviço. Recalculado pelo service layer (ReviewService);
aqui só há consultas.
"""
from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from django.db.models import Q, QuerySet

from beauty_formula.apps.services.models.service_average_rating import ServiceAverageRating

# select_related padrão pra qualquer listagem/detalhe que vá virar
# ServiceAverageRatingOut — evita N+1 ao montar o serviço aninhado.
DEFAULT_RELATED = ("service",)


# ═══════════════════════════════════════════════════════════════════════════════
# Buscas Básicas por ID
# ═══════════════════════════════════════════════════════════════════════════════

def get_service_average_rating_by_id(rating_id: UUID) -> Optional[ServiceAverageRating]:
    """Retorna o agregado pelo ID, ou None se não existir."""
    return ServiceAverageRating.objects.select_related(*DEFAULT_RELATED).filter(id=rating_id).first()


# ═══════════════════════════════════════════════════════════════════════════════
# Buscas por Serviço
# ═══════════════════════════════════════════════════════════════════════════════

def get_average_rating_for_service(service_id: UUID) -> Optional[ServiceAverageRating]:
    """Retorna o agregado de avaliação de um serviço específico (OneToOne)."""
    return ServiceAverageRating.objects.select_related(*DEFAULT_RELATED).filter(service_id=service_id).first()


def get_average_ratings_for_services(service_ids: List[UUID]) -> QuerySet[ServiceAverageRating]:
    """Retorna os agregados de avaliação de múltiplos serviços por uma lista de IDs."""
    if not service_ids:
        return ServiceAverageRating.objects.none()
    return ServiceAverageRating.objects.select_related(*DEFAULT_RELATED).filter(service_id__in=service_ids)


# ═══════════════════════════════════════════════════════════════════════════════
# Listagem Geral
# ═══════════════════════════════════════════════════════════════════════════════

def get_all_service_average_ratings() -> QuerySet[ServiceAverageRating]:
    """Retorna todos os agregados de avaliação de serviço, sem filtro."""
    return ServiceAverageRating.objects.select_related(*DEFAULT_RELATED).all().order_by("-average_rating")


def get_services_with_reviews() -> QuerySet[ServiceAverageRating]:
    """Retorna apenas serviços que já possuem ao menos uma avaliação."""
    return (
        ServiceAverageRating.objects.select_related(*DEFAULT_RELATED)
        .filter(total_reviews__gt=0)
        .order_by("-average_rating")
    )


def get_services_without_reviews() -> QuerySet[ServiceAverageRating]:
    """Retorna serviços que ainda não possuem nenhuma avaliação."""
    return ServiceAverageRating.objects.select_related(*DEFAULT_RELATED).filter(total_reviews=0)


# ═══════════════════════════════════════════════════════════════════════════════
# Buscas por Melhor/Pior Avaliação
# ═══════════════════════════════════════════════════════════════════════════════

def get_top_rated_services(limit: int = 10) -> QuerySet[ServiceAverageRating]:
    """Retorna os serviços com melhor média de avaliação."""
    return (
        ServiceAverageRating.objects.select_related(*DEFAULT_RELATED)
        .filter(total_reviews__gt=0)
        .order_by("-average_rating")[:limit]
    )


def get_worst_rated_services(limit: int = 10) -> QuerySet[ServiceAverageRating]:
    """Retorna os serviços com pior média de avaliação."""
    return (
        ServiceAverageRating.objects.select_related(*DEFAULT_RELATED)
        .filter(total_reviews__gt=0)
        .order_by("average_rating")[:limit]
    )


# ═══════════════════════════════════════════════════════════════════════════════
# Filtros Avançados
# ═══════════════════════════════════════════════════════════════════════════════

def filter_service_average_ratings(
    min_average_rating: Optional[Decimal] = None,
    max_average_rating: Optional[Decimal] = None,
    min_total_reviews: Optional[int] = None,
) -> QuerySet[ServiceAverageRating]:
    """Listagem de agregados de serviço com filtros combináveis. Nenhum filtro informado retorna tudo."""
    q = Q()

    if min_average_rating is not None:
        q &= Q(average_rating__gte=min_average_rating)
    if max_average_rating is not None:
        q &= Q(average_rating__lte=max_average_rating)
    if min_total_reviews is not None:
        q &= Q(total_reviews__gte=min_total_reviews)

    qs = ServiceAverageRating.objects.select_related(*DEFAULT_RELATED).filter(q) if q else ServiceAverageRating.objects.select_related(*DEFAULT_RELATED).all()
    return qs.order_by("-average_rating")


# ═══════════════════════════════════════════════════════════════════════════════
# Utilitários
# ═══════════════════════════════════════════════════════════════════════════════

def validate_service_average_rating_exists(service_id: UUID) -> bool:
    """Verifica se já existe agregado de avaliação para o serviço."""
    return ServiceAverageRating.objects.filter(service_id=service_id).exists()