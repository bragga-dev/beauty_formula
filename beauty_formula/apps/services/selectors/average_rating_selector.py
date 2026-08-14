"""
Queries de AverageRating — avaliações reais deixadas pelos clientes sobre
atendimentos concluídos. Fonte de dados brutos do domínio de avaliações.
"""
from typing import Optional
from uuid import UUID

from django.db.models import Q, QuerySet

from beauty_formula.apps.services.models.average_rating import AverageRating

# select_related padrão pra qualquer listagem/detalhe que vá virar
# AverageRatingOut/AverageRatingPrivateOut — evita N+1 ao montar client/
# employee/service aninhados.
DEFAULT_RELATED = ("client", "client__user", "employee", "employee__user", "service")


# ═══════════════════════════════════════════════════════════════════════════════
# Buscas Básicas por ID
# ═══════════════════════════════════════════════════════════════════════════════

def get_average_rating_by_id(rating_id: UUID) -> Optional[AverageRating]:
    """Retorna a avaliação pelo ID, ou None se não existir."""
    return AverageRating.objects.select_related(*DEFAULT_RELATED).filter(id=rating_id).first()


def get_average_rating_by_scheduling(scheduling_id: UUID) -> Optional[AverageRating]:
    """Retorna a avaliação vinculada a um agendamento específico (OneToOne)."""
    return AverageRating.objects.select_related(*DEFAULT_RELATED).filter(scheduling_id=scheduling_id).first()


# ═══════════════════════════════════════════════════════════════════════════════
# Listagem por Serviço
# ═══════════════════════════════════════════════════════════════════════════════

def get_ratings_by_service(service_id: UUID, authorized_only: bool = True) -> QuerySet[AverageRating]:
    """Retorna as avaliações de um serviço específico."""
    qs = AverageRating.objects.select_related(*DEFAULT_RELATED).filter(service_id=service_id)
    if authorized_only:
        qs = qs.filter(is_authorized=True)
    return qs.order_by("-rating", "-created_at")


# ═══════════════════════════════════════════════════════════════════════════════
# Listagem por Funcionário
# ═══════════════════════════════════════════════════════════════════════════════

def get_ratings_by_employee(employee_id: UUID, authorized_only: bool = True) -> QuerySet[AverageRating]:
    """Retorna as avaliações recebidas por um funcionário específico."""
    qs = AverageRating.objects.select_related(*DEFAULT_RELATED).filter(employee_id=employee_id)
    if authorized_only:
        qs = qs.filter(is_authorized=True)
    return qs.order_by("-rating", "-created_at")


# ═══════════════════════════════════════════════════════════════════════════════
# Listagem por Cliente
# ═══════════════════════════════════════════════════════════════════════════════

def get_ratings_by_client(client_id: UUID) -> QuerySet[AverageRating]:
    """Retorna todas as avaliações feitas por um cliente específico."""
    return AverageRating.objects.select_related(*DEFAULT_RELATED).filter(client_id=client_id).order_by("-rating", "-created_at")


# ═══════════════════════════════════════════════════════════════════════════════
# Listagem por Nota
# ═══════════════════════════════════════════════════════════════════════════════

def get_ratings_by_stars(rating: int, authorized_only: bool = True) -> QuerySet[AverageRating]:
    """Retorna as avaliações com uma nota específica (1 a 5 estrelas)."""
    qs = AverageRating.objects.select_related(*DEFAULT_RELATED).filter(rating=rating)
    if authorized_only:
        qs = qs.filter(is_authorized=True)
    return qs.order_by("-created_at")


# ═══════════════════════════════════════════════════════════════════════════════
# Listagem por Autorização
# ═══════════════════════════════════════════════════════════════════════════════

def get_pending_authorization_ratings() -> QuerySet[AverageRating]:
    """Retorna as avaliações ainda não autorizadas (aguardando moderação)."""
    return AverageRating.objects.select_related(*DEFAULT_RELATED).filter(is_authorized=False).order_by("-rating", "-created_at")


def get_authorized_ratings() -> QuerySet[AverageRating]:
    """Retorna apenas as avaliações já autorizadas (públicas)."""
    return AverageRating.objects.select_related(*DEFAULT_RELATED).filter(is_authorized=True).order_by("-rating", "-created_at")


# ═══════════════════════════════════════════════════════════════════════════════
# Listagem com Comentário
# ═══════════════════════════════════════════════════════════════════════════════

def get_ratings_with_comment(authorized_only: bool = True) -> QuerySet[AverageRating]:
    """Retorna avaliações que possuem comentário preenchido."""
    qs = AverageRating.objects.select_related(*DEFAULT_RELATED).exclude(comment__isnull=True).exclude(comment="")
    if authorized_only:
        qs = qs.filter(is_authorized=True)
    return qs.order_by("-rating", "-created_at")


# ═══════════════════════════════════════════════════════════════════════════════
# Filtros Avançados
# ═══════════════════════════════════════════════════════════════════════════════

def filter_average_ratings(
    service_id: Optional[UUID] = None,
    employee_id: Optional[UUID] = None,
    client_id: Optional[UUID] = None,
    rating: Optional[int] = None,
    is_authorized: Optional[bool] = None,
) -> QuerySet[AverageRating]:
    """
    Listagem administrativa de avaliações com filtros combináveis.
    Nenhum filtro informado retorna tudo.
    """
    q = Q()

    if service_id:
        q &= Q(service_id=service_id)
    if employee_id:
        q &= Q(employee_id=employee_id)
    if client_id:
        q &= Q(client_id=client_id)
    if rating is not None:
        q &= Q(rating=rating)
    if is_authorized is not None:
        q &= Q(is_authorized=is_authorized)

    qs = AverageRating.objects.select_related(*DEFAULT_RELATED).filter(q) if q else AverageRating.objects.select_related(*DEFAULT_RELATED).all()
    return qs.order_by("-created_at")


# ═══════════════════════════════════════════════════════════════════════════════
# Utilitários
# ═══════════════════════════════════════════════════════════════════════════════

def validate_average_rating_exists(rating_id: UUID) -> bool:
    """Verifica se uma avaliação existe."""
    return AverageRating.objects.filter(id=rating_id).exists()


def validate_scheduling_already_rated(scheduling_id: UUID) -> bool:
    """Verifica se um agendamento já possui avaliação (respeita a relação OneToOne)."""
    return AverageRating.objects.filter(scheduling_id=scheduling_id).exists()


def get_rating_for_client_service_employee(client_id: UUID, service_id: UUID, employee_id: UUID) -> Optional[AverageRating]:
    """
    Retorna a avaliação existente (se houver) pra essa combinação de
    cliente/serviço/funcionário. Base da regra de unicidade: cada
    cliente avalia UMA vez cada serviço com cada profissional — mesmo
    que repita o atendimento em outro agendamento, avalia de novo
    editando essa avaliação, não criando outra linha na tabela.
    """
    return AverageRating.objects.filter(
        client_id=client_id, service_id=service_id, employee_id=employee_id
    ).first()