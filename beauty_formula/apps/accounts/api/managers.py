"""
Managers endpoints — CRUD de gerente.
Cadastro exclusivo do admin root; demais operações para admin ou gerente.
"""
import uuid
from django.core.exceptions import ValidationError as DjangoValidationError
from django_ratelimit.decorators import ratelimit
from ninja import File, Router, UploadedFile

from beauty_formula.apps.accounts.schemas.manager_schema import (
    ManagerCreateIn,
    ManagerOut,
    ManagerUpdateIn,
)
from beauty_formula.apps.accounts.schemas.user_schema import MessageOut
from beauty_formula.apps.accounts.selectors.manager_selector import get_managers
from beauty_formula.apps.accounts.services.manager_service import (
    delete_manager_photo,
    get_manager,
    register_manager,
    remove_manager,
    update_manager_profile,
    upload_manager_photo,
)
from beauty_formula.apps.core.exceptions.media import InvalidImageFile
from beauty_formula.apps.core.exceptions.user import (
    AccountHasProtectedRecords,
    UserAlreadyExists,
    UserNotFound,
)
from beauty_formula.apps.core.permissions.auth_classes import AdminOnlyAuth, AdminOrManagerAuth
from beauty_formula.apps.core.schemas.deafult_schema import PageOut
from beauty_formula.apps.core.utils.pagination import paginate_queryset

router = Router()


@router.post(
    "/",
    response={201: ManagerOut, 409: MessageOut},
    auth=AdminOnlyAuth(),
    summary="Cadastro de Gerente (somente admin root)",
    description=(
        "Cria o gerente e envia a senha temporária por e-mail. Não retorna "
        "tokens de sessão."
    ),
)
@ratelimit(key="ip", rate="20/h", block=True)
def create_manager_router(request, payload: ManagerCreateIn):
    try:
        return 201, register_manager(payload)
    except UserAlreadyExists as e:
        return 409, {"detail": str(e)}


@router.get(
    "/",
    response={200: PageOut[ManagerOut]},
    auth=AdminOrManagerAuth(),
    summary="Lista gerentes",
)
def list_managers_router(request, page: int = 1, page_size: int = 20):
    return 200, paginate_queryset(get_managers(), page, page_size, ManagerOut.from_orm)


@router.get(
    "/{manager_id}",
    response={200: ManagerOut, 404: MessageOut},
    auth=AdminOrManagerAuth(),
    summary="Detalhe de um gerente",
)
def get_manager_router(request, manager_id: uuid.UUID):
    try:
        return 200, get_manager(manager_id)
    except UserNotFound as e:
        return 404, {"detail": str(e)}


@router.patch(
    "/{manager_id}",
    response={200: ManagerOut, 400: MessageOut, 404: MessageOut},
    auth=AdminOrManagerAuth(),
    summary="Atualiza os dados de um gerente",
)
@ratelimit(key="user", rate="20/m", block=True)
def update_manager_router(request, manager_id: uuid.UUID, payload: ManagerUpdateIn):
    try:
        return 200, update_manager_profile(manager_id, payload)
    except UserNotFound as e:
        return 404, {"detail": str(e)}
    except DjangoValidationError as e:
        return 400, {"detail": "; ".join(e.messages) if hasattr(e, "messages") else str(e)}


@router.post(
    "/{manager_id}/photo",
    response={200: ManagerOut, 400: MessageOut, 404: MessageOut},
    auth=AdminOrManagerAuth(),
    summary="Substitui a foto de um gerente",
)
@ratelimit(key="user", rate="10/h", block=True)
def upload_manager_photo_router(request, manager_id: uuid.UUID, photo: UploadedFile = File(...)):
    try:
        return 200, upload_manager_photo(manager_id, photo)
    except UserNotFound as e:
        return 404, {"detail": str(e)}
    except InvalidImageFile as e:
        return 400, {"detail": str(e)}


@router.delete(
    "/{manager_id}/photo",
    response={200: ManagerOut, 404: MessageOut},
    auth=AdminOrManagerAuth(),
    summary="Remove a foto de um gerente (volta para a padrão)",
)
@ratelimit(key="user", rate="10/h", block=True)
def delete_manager_photo_router(request, manager_id: uuid.UUID):
    try:
        return 200, delete_manager_photo(manager_id)
    except UserNotFound as e:
        return 404, {"detail": str(e)}


@router.delete(
    "/{manager_id}",
    response={204: None, 404: MessageOut, 409: MessageOut},
    auth=AdminOrManagerAuth(),
    summary="Exclui um gerente",
)
@ratelimit(key="user", rate="10/h", block=True)
def delete_manager_router(request, manager_id: uuid.UUID):
    try:
        remove_manager(manager_id)
        return 204, None
    except UserNotFound as e:
        return 404, {"detail": str(e)}
    except AccountHasProtectedRecords as e:
        return 409, {"detail": str(e)}