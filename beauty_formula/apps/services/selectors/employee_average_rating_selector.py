"""
Queries de EmployeeAverageRating — agregado de leitura (cache) com a média
de avaliações por funcionário. Recalculado pelo service layer (ReviewService);
aqui só há consultas.
"""
from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from django.db.models import Q, QuerySet

from beauty_formula.apps.services.models.employee_average_rating import EmployeeAverageRating

# select_related padrão pra qualquer listagem/detalhe que vá virar
# EmployeeAverageRatingOut — evita N+1 ao montar o funcionário aninhado.
DEFAULT_RELATED = ("employee", "employee__user")


# ═══════════════════════════════════════════════════════════════════════════════
# Buscas Básicas por ID
# ═══════════════════════════════════════════════════════════════════════════════

def get_employee_average_rating_by_id(rating_id: UUID) -> Optional[EmployeeAverageRating]:
    """Retorna o agregado pelo ID, ou None se não existir."""
    return EmployeeAverageRating.objects.select_related(*DEFAULT_RELATED).filter(id=rating_id).first()


# ═══════════════════════════════════════════════════════════════════════════════
# Buscas por Funcionário
# ═══════════════════════════════════════════════════════════════════════════════

def get_average_rating_for_employee(employee_id: UUID) -> Optional[EmployeeAverageRating]:
    """Retorna o agregado de avaliação de um funcionário específico (OneToOne)."""
    return EmployeeAverageRating.objects.select_related(*DEFAULT_RELATED).filter(employee_id=employee_id).first()


def get_average_ratings_for_employees(employee_ids: List[UUID]) -> QuerySet[EmployeeAverageRating]:
    """Retorna os agregados de avaliação de múltiplos funcionários por uma lista de IDs."""
    if not employee_ids:
        return EmployeeAverageRating.objects.none()
    return EmployeeAverageRating.objects.select_related(*DEFAULT_RELATED).filter(employee_id__in=employee_ids)


# ═══════════════════════════════════════════════════════════════════════════════
# Listagem Geral
# ═══════════════════════════════════════════════════════════════════════════════

def get_all_employee_average_ratings() -> QuerySet[EmployeeAverageRating]:
    """Retorna todos os agregados de avaliação de funcionário, sem filtro."""
    return EmployeeAverageRating.objects.select_related(*DEFAULT_RELATED).all().order_by("-average_rating")


def get_employees_with_reviews() -> QuerySet[EmployeeAverageRating]:
    """Retorna apenas funcionários que já possuem ao menos uma avaliação."""
    return (
        EmployeeAverageRating.objects.select_related(*DEFAULT_RELATED)
        .filter(total_reviews__gt=0)
        .order_by("-average_rating")
    )


def get_employees_without_reviews() -> QuerySet[EmployeeAverageRating]:
    """Retorna funcionários que ainda não possuem nenhuma avaliação."""
    return EmployeeAverageRating.objects.select_related(*DEFAULT_RELATED).filter(total_reviews=0)


# ═══════════════════════════════════════════════════════════════════════════════
# Buscas por Melhor/Pior Avaliação
# ═══════════════════════════════════════════════════════════════════════════════

def get_top_rated_employees(limit: int = 10) -> QuerySet[EmployeeAverageRating]:
    """Retorna os funcionários com melhor média de avaliação."""
    return (
        EmployeeAverageRating.objects.select_related(*DEFAULT_RELATED)
        .filter(total_reviews__gt=0)
        .order_by("-average_rating")[:limit]
    )


def get_worst_rated_employees(limit: int = 10) -> QuerySet[EmployeeAverageRating]:
    """Retorna os funcionários com pior média de avaliação."""
    return (
        EmployeeAverageRating.objects.select_related(*DEFAULT_RELATED)
        .filter(total_reviews__gt=0)
        .order_by("average_rating")[:limit]
    )


# ═══════════════════════════════════════════════════════════════════════════════
# Filtros Avançados
# ═══════════════════════════════════════════════════════════════════════════════

def filter_employee_average_ratings(
    min_average_rating: Optional[Decimal] = None,
    max_average_rating: Optional[Decimal] = None,
    min_total_reviews: Optional[int] = None,
) -> QuerySet[EmployeeAverageRating]:
    """Listagem de agregados de funcionário com filtros combináveis. Nenhum filtro informado retorna tudo."""
    q = Q()

    if min_average_rating is not None:
        q &= Q(average_rating__gte=min_average_rating)
    if max_average_rating is not None:
        q &= Q(average_rating__lte=max_average_rating)
    if min_total_reviews is not None:
        q &= Q(total_reviews__gte=min_total_reviews)

    qs = EmployeeAverageRating.objects.select_related(*DEFAULT_RELATED).filter(q) if q else EmployeeAverageRating.objects.select_related(*DEFAULT_RELATED).all()
    return qs.order_by("-average_rating")


# ═══════════════════════════════════════════════════════════════════════════════
# Utilitários
# ═══════════════════════════════════════════════════════════════════════════════

def validate_employee_average_rating_exists(employee_id: UUID) -> bool:
    """Verifica se já existe agregado de avaliação para o funcionário."""
    return EmployeeAverageRating.objects.filter(employee_id=employee_id).exists()