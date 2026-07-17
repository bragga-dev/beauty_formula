"""
Login endpoint — autenticação de usuários.
"""
import uuid
from django.conf import settings
from django.http import HttpResponseRedirect
from django_ratelimit.decorators import ratelimit
from ninja import Router
from ninja_jwt.authentication import JWTAuth

from beauty_formula.apps.accounts.services.auth_service import (
    change_password,
    confirm_password_reset,
    login_user,
    logout_user,
    refresh_access_token,
    request_password_reset,
)
from beauty_formula.apps.accounts.services.user_service import (
    deactivate_account,
    login_or_register_client_google,
    register_user_default_client,
    register_user_default_employee,
    promote_client_to_employee,
    get_current_user_profile,
)
from beauty_formula.apps.accounts.services.verification import verify_email

from beauty_formula.apps.accounts.schemas.employee_schema import EmployeeOut
from beauty_formula.apps.accounts.schemas.user_schema import (
    ChangePasswordIn,
    GoogleLoginIn,
    LoginIn,
    MessageOut,
    PasswordResetConfirmIn,
    PasswordResetRequestIn,
    RefreshIn,
    RegisterIn,
    TokenOut,
)

from beauty_formula.apps.accounts.schemas.me_schema import MeOut

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
    InvalidPassword,
    InvalidToken, 
    UserAlreadyExists, 
    UserNotFound,
)

from beauty_formula.apps.core.permissions.auth_classes import AdminOnlyAuth
from beauty_formula.apps.accounts.schemas.user_schema import UserOut
router = Router()

 
@router.get(
    "/me",
    response={200: MeOut, 401: MessageOut, 404: MessageOut},
    auth=JWTAuth(),
    summary="Dados do usuário logado",
    description=(
        "Retorna o usuário autenticado junto com o profile correspondente "
        "à sua role: `client` (Cliente), `employee` (Funcionário) ou nenhum "
        "dos dois (Admin, que não tem profile)."
    ),
)
def me_router(request):
    try:
        return 200, get_current_user_profile(request.auth.id)
    except UserNotFound as e:
        return 404, {"detail": str(e)}




@router.post("/login", response={200: TokenOut, 401: MessageOut, 403: MessageOut}, auth=None, summary="Login")
@ratelimit(key="ip", rate="5/m", block=True)
def login_router(request, payload: LoginIn):
    try:
        tokens = login_user(payload.email, payload.password)
        return 200, tokens
    except EmailNotVerified:
        return 403, {"detail": "E-mail não verificado."}
    except InvalidCredentials:
        return 401, {"detail": "E-mail ou senha inválidos."}
    

@router.post(
    "/google",
    response={200: TokenOut, 201: TokenOut, 401: MessageOut},
    auth=None,
    summary="Login/Cadastro de Cliente via Google",
    description=(
        "Recebe o id_token (credential) emitido pelo Google Identity Services "
        "no frontend. Se já existir um usuário com o e-mail da conta Google, "
        "efetua login (200). Caso contrário, cria um novo Cliente já verificado (201). "
        "Sempre cadastra/loga com role 'client'."
    ),
)
@ratelimit(key="ip", rate="10/m", block=True)
def google_login_router(request, payload: GoogleLoginIn):
    try:
        tokens, created = login_or_register_client_google(payload.id_token)
        return (201 if created else 200), tokens
    except InvalidGoogleToken as e:
        return 401, {"detail": str(e)}


@router.post("/logout", response={200: MessageOut, 401: MessageOut},  auth=JWTAuth(), summary="Logout (blacklista o refresh token)",)
@ratelimit(key="user", rate="30/m", block=True)
def logout_router(request, payload: RefreshIn):
    try:
        logout_user(payload.refresh)
        return 200, {"detail": "Logout realizado com sucesso."}
    except InvalidToken as e:
        return 401, {"detail": str(e)}
    

@router.post("/password-reset/request", response={200: MessageOut}, auth=None, summary="Solicitar reset de senha",)
@ratelimit(key="ip", rate="5/h", block=True,)
def password_reset_request_router(request, payload: PasswordResetRequestIn):
    request_password_reset(payload.email)
    return 200, {"detail": "Se este e-mail estiver cadastrado, você receberá as instruções em breve."}


@router.post("/password-reset/confirm", response={200: MessageOut, 400: MessageOut},  auth=None, summary="Confirmar reset de senha",)
@ratelimit(key="ip", rate="30/h",  block=True,)
def password_reset_confirm_router(request, payload: PasswordResetConfirmIn):
    try:
        confirm_password_reset(
            uidb64=payload.uid,
            token=payload.token,
            new_password=payload.new_password,
        )
        return 200, {"detail": "Senha redefinida com sucesso."}
    except InvalidToken:
        return 400, {"detail": "Token inválido ou expirado."}


@router.post("/refresh", response={200: dict, 401: MessageOut}, auth=None, summary="Renovar access token",)
@ratelimit(key="ip", rate="30/m",  block=True,)
def refresh_router(request, payload: RefreshIn):
    try:
        data = refresh_access_token(payload.refresh)
        return 200, data
    except InvalidToken as e:
        return 401, {"detail": str(e)}
    

@router.post("/register", response={201: TokenOut, 409: MessageOut}, auth=None, summary="Cadastro de Cliente",)
@ratelimit(key="ip", rate="5/h", block=True,)
def register_router(request, payload: RegisterIn):
    """
    Cria o usuário com role "client" e retorna tokens JWT.
    Um e-mail de verificação é enviado em background via Celery.
    """
    try:
        tokens = register_user_default_client(payload)
        return 201, tokens
    except UserAlreadyExists as e:
        return 409, {"detail": str(e)}
    



@router.get("/verify-email/{uidb64}/{token}", summary="Confirmar e-mail",  description="Confirma o email e redireciona para o frontend.", auth=None,)
@ratelimit( key="ip", rate="20/h", block=True,)
def verify_email_endpoint_router(request, uidb64: str, token: str):
    """
    Confirma o email e redireciona para o frontend.
    """
    try:
        user = verify_email(uidb64, token)
        redirect_url = f"{settings.FRONTEND_URL}/verificacao-concluida?status=success&email={user.email}"
        return HttpResponseRedirect(redirect_url)
    except InvalidToken as e:
        redirect_url = f"{settings.FRONTEND_URL}/verificacao-concluida?status=error&message={str(e)}"
        return HttpResponseRedirect(redirect_url)
    
@router.post("/resend-verification", response={200: MessageOut, 404: MessageOut}, summary="Reenviar email de verificação", auth=None, )
@ratelimit(key="ip", rate="3/h", block=True,)
def resend_verification_email_router(request, email: str):
    """
    Reenvia o email de verificação para um usuário não verificado.
    """    
    user = get_user_by_email(email)
    if not user or user.is_active:
        return 404, {"detail": "Usuário não encontrado ou já verificado."}
    
    send_verification_email.delay(user.pk)
    return 200, {"detail": "Email de verificação reenviado com sucesso."}




@router.post("/change-password",  response={200: TokenOut, 400: MessageOut, 429: MessageOut},
        auth=JWTAuth(), summary="Alterar senha", description=(
        "Troca a senha do usuário autenticado. "
        "Todos os tokens anteriores são invalidados e um novo par é retornado."
    ),
)
@ratelimit(key="user", rate="5/h", block=True)
def change_password_router(request, payload: ChangePasswordIn):
    try:
        tokens = change_password(
            user=request.auth,
            old_password=payload.old_password,
            new_password=payload.new_password,
        )
        return 200, tokens
    except InvalidPassword as e:
        return 400, {"detail": str(e)}
    




@router.post("/register-employee", response={201: TokenOut, 409: MessageOut}, auth=AdminOnlyAuth(), summary="Cadastro de Funcionário",)
@ratelimit(key="ip", rate="20/h", block=True,)
def register_employee_router(request, payload: RegisterIn):
    """
    Cria o usuário com role "employee" e retorna tokens JWT.
    Um e-mail de verificação é enviado em background via Celery.
    """
    try:
        tokens = register_user_default_employee(payload)
        return 201, tokens
    except UserAlreadyExists as e:
        return 409, {"detail": str(e)}

@router.post("/promote-client-to-employee/{user_id}", response={201: EmployeeOut, 404: MessageOut, 400: MessageOut}, auth=AdminOnlyAuth(), summary="Promove Cliente a Funcionário.")
@ratelimit(key="ip", rate="20/h", block=True)
def promote_to_employee_router(request, user_id: uuid.UUID):
    try:
        employee = promote_client_to_employee(user_id, performed_by=request.auth)
        return 201, EmployeeOut.from_orm(employee=employee)
    except UserNotFound as e:
        return 404, {"detail": str(e)}
    except Exception as e:
        return 400, {"detail": f"Erro ao promover cliente: {str(e)}"}
    

@router.post("/deactive-user/{user_id}", response={201: UserOut, 404: MessageOut, 400: MessageOut}, auth=AdminOnlyAuth(), summary="Desativa Usuário.")
@ratelimit(key="ip", rate="20/h", block=True)
def deactivate_account_router(request, user_id: uuid.UUID):
    try:
        user = deactivate_account(user_id, performed_by=request.auth)
        return 201, UserOut.from_orm(user=user)
    except UserNotFound as e:
        return 404, {"detail": str(e)}
    except Exception as e:
        return 400, {"detail": f"Erro ao desativar usuário: {str(e)}"}