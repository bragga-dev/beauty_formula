"""
Login endpoint — autenticação de usuários.
"""
import uuid
from typing import Optional, List
from django.conf import settings
from django.http import HttpResponseRedirect
from django_ratelimit.decorators import ratelimit
from ninja import File, Router, UploadedFile
from ninja_jwt.authentication import JWTAuth

from beauty_formula.apps.services.services.service_service import (
    create_service_for_admin,
    update_service_for_admin,
    list_all_public_services,
    detail_service,
    delete_service_for_admin,
)
from beauty_formula.apps.accounts.services.user_service import (
    deactivate_account,
    delete_own_account,
    export_user_data,
    login_or_register_client_google,
    reactivate_user,
    register_user_default_client,
    register_user_default_employee,
    promote_client_to_employee,
    get_current_user_profile,
    update_client_profile,
    update_employee_profile,
    
    
)
from beauty_formula.apps.accounts.services.client_service import (
    upload_client_profile_photo,
    delete_client_profile_photo,
)

from beauty_formula.apps.accounts.services.employee_service import (
    upload_employee_profile_photo,
    delete_employee_profile_photo,
)
from beauty_formula.apps.accounts.services.verification import verify_email

from beauty_formula.apps.accounts.schemas.employee_schema import EmployeeOut, EmployeeUpdateIn
from beauty_formula.apps.accounts.schemas.client_schema import ClientOut, ClientUpdateIn
from beauty_formula.apps.accounts.schemas.user_schema import (
    ChangePasswordIn,
    DeleteAccountIn,
    GoogleLoginIn,
    LoginIn,
    MessageOut,
    PasswordResetConfirmIn,
    PasswordResetRequestIn,
    RefreshIn,
    RegisterIn,
    RegisterEmployeeIn,
    SessionOut,
    TokenOut,
)

from beauty_formula.apps.services.schemas.service_schema import (
    ServiceCreateIn,
    ServiceOut,
    ServiceFilter,
    ServiceUpdateIn,
    )

from beauty_formula.apps.accounts.schemas.employee_schema import PromoteToEmployeeIn

from beauty_formula.apps.accounts.selectors.user_selector import get_user_by_email

from beauty_formula.apps.accounts.tasks.verification_account import send_verification_email

from beauty_formula.apps.core.exceptions import (
    EmailNotVerified,
    InvalidCredentials,
    InvalidPassword,
    InvalidToken,
    UserAlreadyExists,
)

from beauty_formula.apps.core.exceptions import (
    EmailNotVerified,
    InvalidCredentials, 
    InvalidGoogleToken,
    InvalidImageFile,
    InvalidPassword,
    InvalidToken, 
    SessionNotFound,
    UserAlreadyExists, 
    UserNotFound,
)

from beauty_formula.apps.core.permissions.auth_classes import (
    AdminOnlyAuth, 
    EmployeeOnlyAuth, 
    ClientOnlyAuth,
    EmployeeOrClientAuth,
    AllRolesAuth,
    AdminOrClientAuth,
    AdminOrEmployeeAuth,
    )
from beauty_formula.apps.core.exceptions.service_exception import ServiceNotFound
from beauty_formula.apps.accounts.schemas.user_schema import UserOut
from beauty_formula.apps.accounts.models.user import User
from beauty_formula.apps.core.exceptions.permissions import PermissionDenied
from beauty_formula.apps.core.utils.pagination import paginate_queryset

router = Router()



router = Router()

from beauty_formula.apps.core.schemas.deafult_schema import PageOut
from beauty_formula.apps.core.utils.pagination import paginate_queryset

@router.get(
    "/list-services",
    response={
        200: PageOut[ServiceOut],
        400: MessageOut,
        403: MessageOut,
        404: MessageOut,
    },
    auth=None,
    summary="Retorna todos os Serviços ativos",
)
@ratelimit(key="ip", rate="10/m", block=True)
def list_services_router(request, page: int = 1, page_size: int = 20):
    """
    Endpoint público para listar todos os serviços ativos.
    """
    try:
        services_qs = list_all_public_services()
        result = paginate_queryset(services_qs, page, page_size, lambda service: service)
        return 200, result
    except PermissionDenied:
        return 403, {"detail": "Acesso negado"}
    except ServiceNotFound as e:
        return 404, {"detail": str(e)}
    except Exception as e:
        return 400, {"detail": str(e)}



@router.get(
    "/detail-service/{service_id}",
    response={
        200: ServiceOut,
        400: MessageOut,
        403: MessageOut,
        404: MessageOut,
    },
    auth=None,
    summary="Retorna um Serviço ativo específico pelo ID",
)
@ratelimit(key="ip", rate="10/m", block=True)
def detail_service_router(request, service_id: uuid.UUID):
    """
    Endpoint público para exibir detalhes de um serviço.
    """
    try:
        service = detail_service(service_id=service_id)
        return 200, service
    except PermissionDenied:
        return 403, {"detail": "Acesso negado"}
    except ServiceNotFound as e:
        return 404, {"detail": str(e)}
    except Exception as e:
        return 400, {"detail": str(e)}


@router.post("/create-service", response={201: ServiceOut, 400: MessageOut, 403: MessageOut},  auth=AdminOnlyAuth(), summary="Cria/Registra um serviço da Barbearia/Salão",)
@ratelimit(key="user", rate="30/m", block=True)
def create_service_router(request, payload: ServiceCreateIn, image: Optional[UploadedFile] = File(None)):
    user: User = request.auth
    try:
        service = create_service_for_admin(user.id, payload, image=image)
        return 201, service
    except PermissionDenied:
        # deixa o handler global (config/api.py) converter em 403
        raise
    except Exception as e:
        return 400, {"detail": str(e)}


@router.patch(
    "/{service_id}",
    response={200: ServiceOut, 400: MessageOut, 403: MessageOut, 404: MessageOut},
    auth=AdminOnlyAuth(),
    summary="Atualiza um serviço existente",
)
@ratelimit(key="user", rate="30/m", block=True)
def update_service_router(request, service_id: uuid.UUID, payload: ServiceUpdateIn):
    user: User = request.auth
    try:
        service = update_service_for_admin(user.id, service_id, payload)
        return 200, service
    except PermissionDenied:
        raise
    except ServiceNotFound as e:
        return 404, {"detail": str(e)}
    except Exception as e:
        return 400, {"detail": str(e)}




@router.delete(
    "/{service_id}",
    response={200: None, 400: MessageOut, 403: MessageOut, 404: MessageOut},
    auth=AdminOnlyAuth(),
    summary="Deleta um serviço existente",
)
@ratelimit(key="user", rate="30/m", block=True)
def delete_service_router(request, service_id: uuid.UUID):
    user: User = request.auth
    try:
        delete_service_for_admin(user.id, service_id)
        return 200, {"detail": "Serviço excluído com sucesso !!!"}
    except PermissionDenied:
        raise
    except ServiceNotFound as e:
        return 404, {"detail": str(e)}
    except Exception as e:
        return 400, {"detail": str(e)}

