"""
Service layer de AverageRating — regras de negócio das avaliações de
atendimento e dos agregados derivados (ServiceAverageRating /
EmployeeAverageRating).

Fluxo:
- Cliente avalia um agendamento CONCLUÍDO próprio (uma vez só, 1:1 com o
  scheduling). `service`/`employee`/`client` são sempre derivados do
  scheduling já validado — nunca confiados do payload.
- Toda avaliação nasce com `is_authorized=False`; só entra nas médias
  públicas depois que um admin autoriza.
- Qualquer criação/edição/exclusão/autorização/revogação de uma avaliação
  recalcula os agregados do serviço e do funcionário envolvidos.
"""
from typing import Optional
from uuid import UUID

from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from beauty_formula.apps.accounts.selectors.client_selector import get_client_by_user_id
from beauty_formula.apps.accounts.selectors.employee_selector import (
    validate_employee_exists,
)
from beauty_formula.apps.core.exceptions.permissions import ClientNotFoundError, EmployeeNotFoundError
from beauty_formula.apps.core.exceptions.service_exception import (
    AverageRatingAlreadyExists,
    AverageRatingNotFound,
    ServiceNotFound,
)
from beauty_formula.apps.core.ownership.scheduling_verification import get_own_client_scheduling
from beauty_formula.apps.services.repositories.average_rating_repository import (
    authorize_rating,
    create_average_rating,
    delete_average_rating,
    revoke_rating_authorization,
    update_rating,
)
from beauty_formula.apps.services.repositories.employee_average_rating_repository import (
    recalculate_employee_average_rating,
)
from beauty_formula.apps.services.repositories.service_average_rating_repository import (
    recalculate_service_average_rating,
)
from beauty_formula.apps.services.schemas.average_rating_schema import (
    AverageRatingCreateIn,
    AverageRatingFilter,
    AverageRatingPrivateOut,
    AverageRatingUpdateIn,
)
from beauty_formula.apps.services.schemas.employee_average_rating_schema import EmployeeAverageRatingOut
from beauty_formula.apps.services.schemas.service_average_rating_schema import ServiceAverageRatingOut
from beauty_formula.apps.services.selectors.average_rating_selector import (
    filter_average_ratings,
    get_average_rating_by_id,
    get_rating_for_client_service_employee,
    get_ratings_by_client,
    get_ratings_by_employee,
    get_ratings_by_service,
    validate_scheduling_already_rated,
)
from beauty_formula.apps.services.selectors.employee_average_rating_selector import (
    get_average_rating_for_employee,
)
from beauty_formula.apps.services.selectors.service_average_rating_selector import (
    get_average_rating_for_service,
)
from beauty_formula.apps.services.selectors.service_selector import validate_service_exists



from beauty_formula.apps.accounts.models.user import User
from beauty_formula.apps.accounts.selectors.employee_selector import get_employee_by_user_id
from beauty_formula.apps.core.exceptions import PermissionDenied
from beauty_formula.apps.core.permissions.roles import is_admin
from beauty_formula.apps.accounts.selectors.user_selector import get_user_by_id
# ═══════════════════════════════════════════════════════════════════════════════
# Helpers internos
# ═══════════════════════════════════════════════════════════════════════════════

def _get_own_average_rating(user_id: UUID, rating_id: UUID):
    """Busca a avaliação garantindo que pertence ao cliente autenticado."""
    client = get_client_by_user_id(user_id=user_id)
    if client is None:
        raise ClientNotFoundError()

    rating = get_average_rating_by_id(rating_id=rating_id)
    if rating is None or rating.client_id != client.id:
        raise AverageRatingNotFound()

    return rating


def _refresh_aggregates(rating) -> None:
    """Recalcula os agregados de serviço e funcionário ligados à avaliação."""
    recalculate_service_average_rating(rating.service)
    recalculate_employee_average_rating(rating.employee)


# ═══════════════════════════════════════════════════════════════════════════════
# Cliente
# ═══════════════════════════════════════════════════════════════════════════════

@transaction.atomic
def create_average_rating_for_client(user_id: UUID, data: AverageRatingCreateIn) -> AverageRatingPrivateOut:
    """
    Cliente avalia um agendamento concluído próprio.

    Regra de unicidade: 1 avaliação por combinação (cliente, serviço,
    funcionário) — não por agendamento. Se o cliente já avaliou esse
    serviço com esse profissional antes (em qualquer agendamento), a
    criação é bloqueada; ele deve editar a avaliação já existente em
    vez de acumular uma nova linha a cada atendimento repetido.
    """
    scheduling = get_own_client_scheduling(user_id=user_id, scheduling_id=data.scheduling_id)

    if validate_scheduling_already_rated(scheduling_id=scheduling.id):
        raise AverageRatingAlreadyExists()

    if get_rating_for_client_service_employee(
        client_id=scheduling.client_id, service_id=scheduling.service_id, employee_id=scheduling.employee_id
    ):
        raise AverageRatingAlreadyExists(
            _("Você já avaliou este serviço com este profissional. Edite sua avaliação existente em vez de criar uma nova.")
        )

    rating = create_average_rating(
        scheduling=scheduling,
        service=scheduling.service,
        employee=scheduling.employee,
        client=scheduling.client,
        rating=data.rating,
        comment=data.comment,
    )

    scheduling.rated_at = timezone.now()
    scheduling.save(update_fields=["rated_at", "updated_at"])

    _refresh_aggregates(rating)
    return AverageRatingPrivateOut.from_orm(rating)

def list_my_average_ratings(user_id: UUID):
    """Lista todas as avaliações do cliente autenticado (autorizadas ou não)."""
    client = get_client_by_user_id(user_id=user_id)
    if client is None:
        raise ClientNotFoundError()
    return get_ratings_by_client(client_id=client.id)


def get_own_average_rating_detail(user_id: UUID, rating_id: UUID) -> AverageRatingPrivateOut:
    rating = _get_own_average_rating(user_id=user_id, rating_id=rating_id)
    return AverageRatingPrivateOut.from_orm(rating)


@transaction.atomic
def update_own_average_rating(user_id: UUID, rating_id: UUID, data: AverageRatingUpdateIn) -> AverageRatingPrivateOut:
    """
    Cliente edita a própria nota/comentário.

    Se a avaliação já estava autorizada (pública) e o cliente muda nota
    ou comentário, ela volta para moderação (`is_authorized=False`) —
    o novo conteúdo precisa passar pelo admin de novo antes de voltar
    a aparecer publicamente.
    """
    rating = _get_own_average_rating(user_id=user_id, rating_id=rating_id)

    fields = data.model_dump(exclude_unset=True)
    content_changed = "rating" in fields or "comment" in fields

    rating = update_rating(rating, **fields)

    if content_changed and rating.is_authorized:
        rating = revoke_rating_authorization(rating)

    if "rating" in fields:
        _refresh_aggregates(rating)

    return AverageRatingPrivateOut.from_orm(rating)

@transaction.atomic
def delete_own_average_rating(user_id: UUID, rating_id: UUID) -> None:
    """Cliente exclui a própria avaliação."""
    rating = _get_own_average_rating(user_id=user_id, rating_id=rating_id)
    service, employee = rating.service, rating.employee

    delete_average_rating(rating)

    recalculate_service_average_rating(service)
    recalculate_employee_average_rating(employee)


# ═══════════════════════════════════════════════════════════════════════════════
# Público (visitantes / clientes / funcionários — leitura)
# ═══════════════════════════════════════════════════════════════════════════════

def list_public_ratings_for_service(service_id: UUID):
    """Lista as avaliações autorizadas de um serviço."""
    if not validate_service_exists(service_id):
        raise ServiceNotFound()
    return get_ratings_by_service(service_id=service_id, authorized_only=True)


def list_public_ratings_for_employee(employee_id: UUID):
    """Lista as avaliações autorizadas de um funcionário."""
    if not validate_employee_exists(employee_id):
        raise EmployeeNotFoundError()
    return get_ratings_by_employee(employee_id=employee_id, authorized_only=True)


def list_all_public_ratings(
    service_id: Optional[UUID] = None,
    employee_id: Optional[UUID] = None,
    rating: Optional[int] = None,
):
    """
    Listagem pública paginável de avaliações autorizadas, com filtros
    combináveis — alimenta a página "Todas as Avaliações". Sempre restrita
    a `is_authorized=True`, independente do que for passado.
    """
    return filter_average_ratings(
        service_id=service_id,
        employee_id=employee_id,
        rating=rating,
        is_authorized=True,
    )


def get_service_rating_summary(service_id: UUID) -> ServiceAverageRatingOut:
    """Média/total de avaliações de um serviço. Zerado se ainda não tem avaliações."""
    if not validate_service_exists(service_id):
        raise ServiceNotFound()

    aggregate = get_average_rating_for_service(service_id=service_id)
    if aggregate is None:
        return ServiceAverageRatingOut(service_id=service_id)
    return ServiceAverageRatingOut.from_orm(aggregate)


def get_employee_rating_summary(employee_id: UUID) -> EmployeeAverageRatingOut:
    """Média/total de avaliações de um funcionário. Zerado se ainda não tem avaliações."""
    if not validate_employee_exists(employee_id):
        raise EmployeeNotFoundError()

    aggregate = get_average_rating_for_employee(employee_id=employee_id)
    if aggregate is None:
        return EmployeeAverageRatingOut(employee_id=employee_id)
    return EmployeeAverageRatingOut.from_orm(aggregate)


# ═══════════════════════════════════════════════════════════════════════════════
# Admin
# ═══════════════════════════════════════════════════════════════════════════════

def list_all_average_ratings_admin(filters: AverageRatingFilter, user_id: UUID):
    """
    Admin lista com os filtros informados livremente. Funcionário só pode
    listar as próprias avaliações — o employee_id é sempre forçado para o
    dele, ignorando qualquer valor vindo do filtro (evita que um
    funcionário veja avaliações de outro trocando o parâmetro).
    """
    user = get_user_by_id(user_id=user_id)
    employee_id = filters.employee_id
    if not is_admin(user):
        employee = get_employee_by_user_id(user_id=user_id)
        if employee is None:
            raise PermissionDenied("Apenas administradores ou funcionários podem acessar este recurso.")
        employee_id = employee.id

    return filter_average_ratings(
        service_id=filters.service_id,
        employee_id=employee_id,
        client_id=filters.client_id,
        rating=filters.rating,
        is_authorized=filters.is_authorized,
    )


def get_average_rating_detail_admin(rating_id: UUID, user_id: UUID) -> AverageRatingPrivateOut:
    """Admin vê qualquer detalhe; funcionário só o detalhe de avaliações sobre ele mesmo."""
    rating = get_average_rating_by_id(rating_id=rating_id)
    if rating is None:
        raise AverageRatingNotFound()
    user = get_user_by_id(user_id=user_id)
    if not is_admin(user):
        employee = get_employee_by_user_id(user_id=user_id)
        if employee is None or rating.employee_id != employee.id:
            raise PermissionDenied("Você só pode ver avaliações sobre você mesmo.")

    return AverageRatingPrivateOut.from_orm(rating)

@transaction.atomic
def authorize_average_rating_admin(user_id:UUID, rating_id: UUID) -> AverageRatingPrivateOut:
    """
    Admin autoriza qualquer avaliação. Funcionário só pode autorizar
    avaliações sobre ELE MESMO — nunca sobre outro funcionário.
    """
    rating = get_average_rating_by_id(rating_id=rating_id)
    if rating is None:
        raise AverageRatingNotFound()
    
    user = get_user_by_id(user_id=user_id)
    if not is_admin(user):
        employee = get_employee_by_user_id(user_id=user_id)
        if employee is None or rating.employee_id != employee.id:
            raise PermissionDenied("Você só pode autorizar avaliações sobre você mesmo.")

    rating = authorize_rating(rating)
    _refresh_aggregates(rating)
    return AverageRatingPrivateOut.from_orm(rating)

@transaction.atomic
def revoke_average_rating_admin(rating_id: UUID) -> AverageRatingPrivateOut:
    """Admin revoga a autorização (ex: comentário ofensivo denunciado)."""
    rating = get_average_rating_by_id(rating_id=rating_id)
    if rating is None:
        raise AverageRatingNotFound()

    rating = revoke_rating_authorization(rating)
    _refresh_aggregates(rating)
    return AverageRatingPrivateOut.from_orm(rating)


@transaction.atomic
def delete_average_rating_admin(rating_id: UUID) -> None:
    """Admin exclui permanentemente uma avaliação."""
    rating = get_average_rating_by_id(rating_id=rating_id)
    if rating is None:
        raise AverageRatingNotFound()
    service, employee = rating.service, rating.employee

    delete_average_rating(rating)

    recalculate_service_average_rating(service)
    recalculate_employee_average_rating(employee)