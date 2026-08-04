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
from uuid import UUID

from django.db import transaction

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
    """Cliente avalia um agendamento concluído próprio (uma vez só)."""
    scheduling = get_own_client_scheduling(user_id=user_id, scheduling_id=data.scheduling_id)

    if validate_scheduling_already_rated(scheduling_id=scheduling.id):
        raise AverageRatingAlreadyExists()

    rating = create_average_rating(
        scheduling=scheduling,
        service=scheduling.service,
        employee=scheduling.employee,
        client=scheduling.client,
        rating=data.rating,
        comment=data.comment,
    )

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
    """Cliente edita a própria nota/comentário."""
    rating = _get_own_average_rating(user_id=user_id, rating_id=rating_id)

    fields = data.model_dump(exclude_unset=True)
    rating = update_rating(rating, **fields)

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

def list_all_average_ratings_admin(filters: AverageRatingFilter):
    return filter_average_ratings(
        service_id=filters.service_id,
        employee_id=filters.employee_id,
        client_id=filters.client_id,
        rating=filters.rating,
        is_authorized=filters.is_authorized,
    )


def get_average_rating_detail_admin(rating_id: UUID) -> AverageRatingPrivateOut:
    rating = get_average_rating_by_id(rating_id=rating_id)
    if rating is None:
        raise AverageRatingNotFound()
    return AverageRatingPrivateOut.from_orm(rating)


@transaction.atomic
def authorize_average_rating_admin(rating_id: UUID) -> AverageRatingPrivateOut:
    """Admin autoriza a avaliação a aparecer publicamente."""
    rating = get_average_rating_by_id(rating_id=rating_id)
    if rating is None:
        raise AverageRatingNotFound()

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