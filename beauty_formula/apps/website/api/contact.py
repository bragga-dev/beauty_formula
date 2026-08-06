"""
Endpoints de Contato — formulário público de contato + gestão administrativa.
"""
import uuid
from typing import Optional

from django_ratelimit.decorators import ratelimit
from ninja import Router

from beauty_formula.apps.website.services.contact_service import (
    create_contact_public,
    list_all_contacts_for_admin,
    detail_contact_for_admin,
    update_contact_status_for_admin,
    delete_contact_for_admin,
)

from beauty_formula.apps.website.schemas.contact_schema import (
    ContactCreateIn,
    ContactUpdateIn,
    ContactOut,
)

from beauty_formula.apps.core.exceptions.contact_exception import (
    ContactNotFound,
    ContactNameAlreadyExists,
)
from beauty_formula.apps.core.permissions.auth_classes import AdminOnlyAuth
from beauty_formula.apps.accounts.schemas.user_schema import MessageOut
from beauty_formula.apps.core.exceptions.permissions import PermissionDenied
from beauty_formula.apps.core.utils.pagination import paginate_queryset, PageOut

router = Router()


@router.post(
    "/create-contact",
    response={201: ContactOut, 400: MessageOut},
    auth=None,
    summary="Envia uma mensagem de contato (formulário público do site)",
)
@ratelimit(key="ip", rate="5/m", block=True)
def create_contact_router(request, payload: ContactCreateIn):
    """
    Endpoint público usado pelo formulário de contato do site.
    """
    try:
        contact = create_contact_public(payload)
        return 201, contact
    except ContactNameAlreadyExists as e:
        return 400, {"detail": str(e)}
    except Exception as e:
        return 400, {"detail": str(e)}


@router.get(
    "/list-contacts",
    response={
        200: PageOut[ContactOut],
        400: MessageOut,
        403: MessageOut,
    },
    auth=AdminOnlyAuth(),
    summary="Retorna todos os Contatos, com filtros opcionais. Apenas Admins podem acessar esse recurso",
)
@ratelimit(key="user", rate="30/m", block=True)
def list_contacts_router(
    request,
    page: int = 1,
    page_size: int = 20,
    search: Optional[str] = None,
    status: Optional[str] = None,
    subject: Optional[str] = None,
):
    try:
        contacts_qs = list_all_contacts_for_admin(search=search, status=status, subject=subject)
        result = paginate_queryset(contacts_qs, page, page_size, lambda contact: contact)
        return 200, result
    except PermissionDenied:
        return 403, {"detail": "Acesso negado"}
    except Exception as e:
        return 400, {"detail": str(e)}


@router.get(
    "/detail-contact/{contact_id}",
    response={
        200: ContactOut,
        400: MessageOut,
        403: MessageOut,
        404: MessageOut,
    },
    auth=AdminOnlyAuth(),
    summary="Retorna um Contato específico pelo ID. Apenas Admins podem acessar esse recurso",
)
@ratelimit(key="user", rate="30/m", block=True)
def detail_contact_router(request, contact_id: uuid.UUID):
    try:
        contact = detail_contact_for_admin(contact_id=contact_id)
        return 200, contact
    except PermissionDenied:
        return 403, {"detail": "Acesso negado"}
    except ContactNotFound as e:
        return 404, {"detail": str(e)}
    except Exception as e:
        return 400, {"detail": str(e)}


@router.patch(
    "/update-contact-status/{contact_id}",
    response={200: ContactOut, 400: MessageOut, 403: MessageOut, 404: MessageOut},
    auth=AdminOnlyAuth(),
    summary="Atualiza o status de um contato existente, apenas Admins podem acessar esse recurso",
)
@ratelimit(key="user", rate="30/m", block=True)
def update_contact_status_router(request, contact_id: uuid.UUID, payload: ContactUpdateIn):
    try:
        contact = update_contact_status_for_admin(contact_id, payload)
        return 200, contact
    except PermissionDenied:
        raise
    except ContactNotFound as e:
        return 404, {"detail": str(e)}
    except Exception as e:
        return 400, {"detail": str(e)}


@router.delete(
    "/delete-contact/{contact_id}",
    response={200: None, 400: MessageOut, 403: MessageOut, 404: MessageOut},
    auth=AdminOnlyAuth(),
    summary="Deleta um contato existente, apenas Admins podem acessar esse recurso",
)
@ratelimit(key="user", rate="30/m", block=True)
def delete_contact_router(request, contact_id: uuid.UUID):
    try:
        delete_contact_for_admin(contact_id)
        return 200, {"detail": "Contato excluído com sucesso !!!"}
    except PermissionDenied:
        raise
    except ContactNotFound as e:
        return 404, {"detail": str(e)}
    except Exception as e:
        return 400, {"detail": str(e)}