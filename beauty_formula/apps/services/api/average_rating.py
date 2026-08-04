"""
Rotas de AverageRating — avaliações de atendimento e seus agregados
(ServiceAverageRating / EmployeeAverageRating).

- Cliente: cria, lista, vê detalhe, edita e exclui as próprias avaliações.
- Público: lista avaliações autorizadas de um serviço/funcionário e
  consulta a média (summary) de cada um.
- Admin: visão total — lista com filtros, vê qualquer detalhe, autoriza,
  revoga e exclui permanentemente.
"""
from typing import Optional
from uuid import UUID

from django_ratelimit.decorators import ratelimit
from ninja import Router

from beauty_formula.apps.accounts.models.user import User
from beauty_formula.apps.accounts.schemas.user_schema import MessageOut
from beauty_formula.apps.core.exceptions.permissions import ClientNotFoundError, EmployeeNotFoundError
from beauty_formula.apps.core.exceptions.service_exception import (
    AverageRatingAlreadyExists,
    AverageRatingNotFound,
    SchedulingNotFound,
    ServiceNotFound,
)
from beauty_formula.apps.core.permissions.auth_classes import (
    AdminOnlyAuth, 
    ClientOnlyAuth, 
    AdminOrEmployeeAuth,

)
from beauty_formula.apps.core.utils.pagination import PAGE_SIZE_DEFAULT, PageOut, paginate_queryset
from beauty_formula.apps.services.schemas.average_rating_schema import (
    AverageRatingCreateIn,
    AverageRatingFilter,
    AverageRatingOut,
    AverageRatingPrivateOut,
    AverageRatingUpdateIn,
    RatingEnum,
)
from beauty_formula.apps.services.schemas.employee_average_rating_schema import EmployeeAverageRatingOut
from beauty_formula.apps.services.schemas.service_average_rating_schema import ServiceAverageRatingOut
from beauty_formula.apps.services.services.average_rating_service import (
    authorize_average_rating_admin,
    create_average_rating_for_client,
    delete_average_rating_admin,
    delete_own_average_rating,
    get_average_rating_detail_admin,
    get_employee_rating_summary,
    get_own_average_rating_detail,
    get_service_rating_summary,
    list_all_average_ratings_admin,
    list_my_average_ratings,
    list_public_ratings_for_employee,
    list_public_ratings_for_service,
    revoke_average_rating_admin,
    update_own_average_rating,
)

router = Router()


# ═══════════════════════════════════════════════════════════════════════════════
# Cliente
# ═══════════════════════════════════════════════════════════════════════════════

@router.post(
    "/create",
    response={201: AverageRatingPrivateOut, 400: MessageOut, 403: MessageOut, 404: MessageOut},
    auth=ClientOnlyAuth(),
    summary="Cliente avalia um agendamento concluído próprio",
)
@ratelimit(key="user", rate="20/m", block=True)
def create_average_rating_router(request, payload: AverageRatingCreateIn):
    user: User = request.auth
    try:
        rating = create_average_rating_for_client(user_id=user.id, data=payload)
        return 201, rating
    except ClientNotFoundError:
        return 404, {"detail": "Cliente não encontrado."}
    except SchedulingNotFound as e:
        return 404, {"detail": str(e)}
    except AverageRatingAlreadyExists as e:
        return 400, {"detail": str(e)}
    except Exception as e:
        return 400, {"detail": str(e)}


@router.get(
    "/my-ratings",
    response={200: PageOut[AverageRatingPrivateOut], 400: MessageOut, 403: MessageOut, 404: MessageOut},
    auth=ClientOnlyAuth(),
    summary="Cliente lista as próprias avaliações (autorizadas ou não)",
)
@ratelimit(key="user", rate="30/m", block=True)
def list_my_average_ratings_router(request, page: int = 1, page_size: int = PAGE_SIZE_DEFAULT):
    user: User = request.auth
    try:
        ratings_qs = list_my_average_ratings(user_id=user.id)
        result = paginate_queryset(ratings_qs, page, page_size, AverageRatingPrivateOut.from_orm)
        return 200, result
    except ClientNotFoundError:
        return 404, {"detail": "Cliente não encontrado."}
    except Exception as e:
        return 400, {"detail": str(e)}


@router.get(
    "/my-ratings/{rating_id}",
    response={200: AverageRatingPrivateOut, 400: MessageOut, 403: MessageOut, 404: MessageOut},
    auth=ClientOnlyAuth(),
    summary="Cliente vê o detalhe de uma avaliação própria",
)
@ratelimit(key="user", rate="30/m", block=True)
def get_my_average_rating_router(request, rating_id: UUID):
    user: User = request.auth
    try:
        rating = get_own_average_rating_detail(user_id=user.id, rating_id=rating_id)
        return 200, rating
    except ClientNotFoundError:
        return 404, {"detail": "Cliente não encontrado."}
    except AverageRatingNotFound as e:
        return 404, {"detail": str(e)}
    except Exception as e:
        return 400, {"detail": str(e)}


@router.patch(
    "/my-ratings/{rating_id}",
    response={200: AverageRatingPrivateOut, 400: MessageOut, 403: MessageOut, 404: MessageOut},
    auth=ClientOnlyAuth(),
    summary="Cliente edita a nota/comentário de uma avaliação própria",
)
@ratelimit(key="user", rate="20/m", block=True)
def update_my_average_rating_router(request, rating_id: UUID, payload: AverageRatingUpdateIn):
    user: User = request.auth
    try:
        rating = update_own_average_rating(user_id=user.id, rating_id=rating_id, data=payload)
        return 200, rating
    except ClientNotFoundError:
        return 404, {"detail": "Cliente não encontrado."}
    except AverageRatingNotFound as e:
        return 404, {"detail": str(e)}
    except Exception as e:
        return 400, {"detail": str(e)}


@router.delete(
    "/my-ratings/{rating_id}",
    response={200: MessageOut, 400: MessageOut, 403: MessageOut, 404: MessageOut},
    auth=ClientOnlyAuth(),
    summary="Cliente exclui uma avaliação própria",
)
@ratelimit(key="user", rate="20/m", block=True)
def delete_my_average_rating_router(request, rating_id: UUID):
    user: User = request.auth
    try:
        delete_own_average_rating(user_id=user.id, rating_id=rating_id)
        return 200, {"detail": "Avaliação excluída com sucesso."}
    except ClientNotFoundError:
        return 404, {"detail": "Cliente não encontrado."}
    except AverageRatingNotFound as e:
        return 404, {"detail": str(e)}
    except Exception as e:
        return 400, {"detail": str(e)}


# ═══════════════════════════════════════════════════════════════════════════════
# Público
# ═══════════════════════════════════════════════════════════════════════════════

@router.get(
    "/service/{service_id}",
    response={200: PageOut[AverageRatingOut], 400: MessageOut, 404: MessageOut},
    summary="Lista as avaliações autorizadas de um serviço",
)
@ratelimit(key="ip", rate="60/m", block=True)
def list_service_ratings_router(request, service_id: UUID, page: int = 1, page_size: int = PAGE_SIZE_DEFAULT):
    try:
        ratings_qs = list_public_ratings_for_service(service_id=service_id)
        result = paginate_queryset(ratings_qs, page, page_size, AverageRatingOut.from_orm)
        return 200, result
    except ServiceNotFound as e:
        return 404, {"detail": str(e)}
    except Exception as e:
        return 400, {"detail": str(e)}


@router.get(
    "/service/{service_id}/summary",
    response={200: ServiceAverageRatingOut, 400: MessageOut, 404: MessageOut},
    summary="Média de avaliações de um serviço",
)
@ratelimit(key="ip", rate="60/m", block=True)
def get_service_rating_summary_router(request, service_id: UUID):
    try:
        return 200, get_service_rating_summary(service_id=service_id)
    except ServiceNotFound as e:
        return 404, {"detail": str(e)}
    except Exception as e:
        return 400, {"detail": str(e)}


@router.get(
    "/employee/{employee_id}",
    response={200: PageOut[AverageRatingOut], 400: MessageOut, 404: MessageOut},
    summary="Lista as avaliações autorizadas de um funcionário",
)
@ratelimit(key="ip", rate="60/m", block=True)
def list_employee_ratings_router(request, employee_id: UUID, page: int = 1, page_size: int = PAGE_SIZE_DEFAULT):
    try:
        ratings_qs = list_public_ratings_for_employee(employee_id=employee_id)
        result = paginate_queryset(ratings_qs, page, page_size, AverageRatingOut.from_orm)
        return 200, result
    except EmployeeNotFoundError:
        return 404, {"detail": "Funcionário não encontrado."}
    except Exception as e:
        return 400, {"detail": str(e)}


@router.get(
    "/employee/{employee_id}/summary",
    response={200: EmployeeAverageRatingOut, 400: MessageOut, 404: MessageOut},
    summary="Média de avaliações de um funcionário",
)
@ratelimit(key="ip", rate="60/m", block=True)
def get_employee_rating_summary_router(request, employee_id: UUID):
    try:
        return 200, get_employee_rating_summary(employee_id=employee_id)
    except EmployeeNotFoundError:
        return 404, {"detail": "Funcionário não encontrado."}
    except Exception as e:
        return 400, {"detail": str(e)}


# ═══════════════════════════════════════════════════════════════════════════════
# Admin
# ═══════════════════════════════════════════════════════════════════════════════

@router.get(
    "/admin/list",
    response={200: PageOut[AverageRatingPrivateOut], 400: MessageOut, 403: MessageOut},
    auth=AdminOnlyAuth(),
    summary="Admin lista todas as avaliações, com filtros combináveis",
)
@ratelimit(key="user", rate="30/m", block=True)
def list_all_average_ratings_router(
    request,
    page: int = 1,
    page_size: int = PAGE_SIZE_DEFAULT,
    service_id: Optional[UUID] = None,
    employee_id: Optional[UUID] = None,
    client_id: Optional[UUID] = None,
    rating: Optional[RatingEnum] = None,
    is_authorized: Optional[bool] = None,
):
    try:
        filters = AverageRatingFilter(
            service_id=service_id,
            employee_id=employee_id,
            client_id=client_id,
            rating=rating,
            is_authorized=is_authorized,
        )
        ratings_qs = list_all_average_ratings_admin(filters=filters)
        result = paginate_queryset(ratings_qs, page, page_size, AverageRatingPrivateOut.from_orm)
        return 200, result
    except Exception as e:
        return 400, {"detail": str(e)}


@router.get(
    "/admin/{rating_id}",
    response={200: AverageRatingPrivateOut, 400: MessageOut, 403: MessageOut, 404: MessageOut},
    auth=AdminOnlyAuth(),
    summary="Admin vê o detalhe completo de qualquer avaliação",
)
@ratelimit(key="user", rate="30/m", block=True)
def get_average_rating_detail_router(request, rating_id: UUID):
    try:
        rating = get_average_rating_detail_admin(rating_id=rating_id)
        return 200, rating
    except AverageRatingNotFound as e:
        return 404, {"detail": str(e)}
    except Exception as e:
        return 400, {"detail": str(e)}


@router.patch(
    "/admin/{rating_id}/authorize",
    response={200: AverageRatingPrivateOut, 400: MessageOut, 403: MessageOut, 404: MessageOut},
    auth=AdminOrEmployeeAuth(),
    summary="Admin ou Funcionário autorizam a avaliação a aparecer publicamente",
)
@ratelimit(key="user", rate="30/m", block=True)
def authorize_average_rating_router(request, rating_id: UUID):
    try:
        rating = authorize_average_rating_admin(rating_id=rating_id)
        return 200, rating
    except AverageRatingNotFound as e:
        return 404, {"detail": str(e)}
    except Exception as e:
        return 400, {"detail": str(e)}


@router.patch(
    "/admin/{rating_id}/revoke",
    response={200: AverageRatingPrivateOut, 400: MessageOut, 403: MessageOut, 404: MessageOut},
    auth=AdminOnlyAuth(),
    summary="Admin revoga a autorização de uma avaliação",
)
@ratelimit(key="user", rate="30/m", block=True)
def revoke_average_rating_router(request, rating_id: UUID):
    try:
        rating = revoke_average_rating_admin(rating_id=rating_id)
        return 200, rating
    except AverageRatingNotFound as e:
        return 404, {"detail": str(e)}
    except Exception as e:
        return 400, {"detail": str(e)}


@router.delete(
    "/admin/{rating_id}",
    response={200: MessageOut, 400: MessageOut, 403: MessageOut, 404: MessageOut},
    auth=AdminOnlyAuth(),
    summary="Admin exclui permanentemente uma avaliação",
)
@ratelimit(key="user", rate="20/m", block=True)
def delete_average_rating_router(request, rating_id: UUID):
    try:
        delete_average_rating_admin(rating_id=rating_id)
        return 200, {"detail": "Avaliação excluída com sucesso."}
    except AverageRatingNotFound as e:
        return 404, {"detail": str(e)}
    except Exception as e:
        return 400, {"detail": str(e)}