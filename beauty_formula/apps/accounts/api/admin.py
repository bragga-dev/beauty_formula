"""
Admin — gestão de usuários (leitura). As ações de escrita (cadastro de
funcionário, promoção de cliente, ativação/desativação) já existem em
`/auth/` (register-employee, promote-client-to-employee, deactive-user,
reactivate-user) e continuam lá para não duplicar rotas de mutação de
User; este router cobre apenas listagem/detalhe para o painel admin.
"""
import uuid
from typing import Optional

from django_ratelimit.decorators import ratelimit
from ninja import Router

from beauty_formula.apps.accounts.models.user import User
from beauty_formula.apps.accounts.schemas.user_schema import (
    MessageOut,
    UserAdminOut,
    UserRoleEnum,
)
from beauty_formula.apps.accounts.selectors.user_selector import get_user_with_related
from beauty_formula.apps.accounts.services.user_service import list_users_admin
from beauty_formula.apps.core.permissions.auth_classes import AdminOnlyAuth
from beauty_formula.apps.core.schemas.deafult_schema import PageOut
from beauty_formula.apps.core.utils.pagination import PAGE_SIZE_DEFAULT, paginate_queryset

router = Router()


@router.get(
    "/list-users",
    response={200: PageOut[UserAdminOut]},
    auth=AdminOnlyAuth(),
    summary="Lista usuários com filtros (busca, role, status)",
    description=(
        "Busca por e-mail ou nome do profile (client/employee). "
        "Filtros de role e status são combináveis com a busca."
    ),
)
@ratelimit(key="user", rate="30/m", block=True)
def list_users_router(
    request,
    page: int = 1,
    page_size: int = PAGE_SIZE_DEFAULT,
    search: Optional[str] = None,
    role: Optional[UserRoleEnum] = None,
    is_active: Optional[bool] = None,
):
    qs = list_users_admin(search=search, role=role.value if role else None, is_active=is_active)
    return 200, paginate_queryset(qs, page, page_size, UserAdminOut.from_orm)


@router.get(
    "/detail-user/{user_id}",
    response={200: UserAdminOut, 404: MessageOut},
    auth=AdminOnlyAuth(),
    summary="Detalhe de um usuário",
)
@ratelimit(key="user", rate="60/m", block=True)
def detail_user_router(request, user_id: uuid.UUID):
    user = get_user_with_related(user_id)
    if not user:
        return 404, {"detail": "Usuário não encontrado."}
    return 200, UserAdminOut.from_orm(user)