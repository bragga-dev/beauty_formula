"""
Login endpoint — autenticação de usuários.
"""
import uuid
from typing import Optional
from django.conf import settings
from django.http import HttpResponseRedirect
from django_ratelimit.decorators import ratelimit
from ninja import File, Router, UploadedFile
from ninja_jwt.authentication import JWTAuth

from beauty_formula.apps.services.services.service_service import (
    create_service_for_admin,
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
from beauty_formula.apps.accounts.schemas.user_schema import UserOut
from beauty_formula.apps.accounts.models.user import User
from beauty_formula.apps.core.exceptions.permissions import PermissionDenied


router = Router()


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