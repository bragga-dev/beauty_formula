"""
Login endpoint — autenticação de usuários.
"""
import uuid
from django.conf import settings
from django.http import HttpResponseRedirect
from django_ratelimit.decorators import ratelimit
from ninja import File, Router, UploadedFile
from ninja_jwt.authentication import JWTAuth

from beauty_formula.apps.accounts.services.auth_service import (
    change_password,
    confirm_password_reset,
    list_active_sessions,
    login_user,
    logout_all_sessions,
    logout_user,
    refresh_access_token,
    request_password_reset,
    revoke_session,
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

from beauty_formula.apps.accounts.schemas.me_schema import (
    MeOut,
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


router = Router()

 
@router.get(
    "/me",
    response={200: MeOut, 401: MessageOut, 404: MessageOut},
    auth=AllRolesAuth(),
    summary="Dados do usuário logado",
    description=(
        "Retorna o usuário autenticado junto com o profile correspondente "
        "à sua role: `client` (Cliente), `employee` (Funcionário) ou nenhum "
        "dos dois (Admin, que não tem profile)."
    ),
)
@ratelimit(key="ip", rate="15/m", block=True)
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


@router.post("/logout", response={200: MessageOut, 401: MessageOut},  auth=AllRolesAuth(), summary="Logout (blacklista o refresh token)",)
@ratelimit(key="user", rate="30/m", block=True)
def logout_router(request, payload: RefreshIn):
    try:
        logout_user(payload.refresh)
        return 200, {"detail": "Logout realizado com sucesso."}
    except InvalidToken as e:
        return 401, {"detail": str(e)}


@router.post(
    "/logout-all",
    response={200: MessageOut},
    auth=JWTAuth(),
    summary="Logout em todos os dispositivos",
    description="Blacklista todos os refresh tokens ativos do usuário logado, encerrando todas as sessões.",
)
@ratelimit(key="user", rate="10/h", block=True)
def logout_all_router(request):
    logout_all_sessions(request.auth)
    return 200, {"detail": "Sessões encerradas em todos os dispositivos."}


@router.get(
    "/sessions",
    response={200: list[SessionOut]},
    auth=AllRolesAuth(),
    summary="Lista sessões ativas",
    description="Lista os refresh tokens ainda válidos (sessões/dispositivos logados) do usuário autenticado.",
)
@ratelimit(key="user", rate="30/m", block=True)
def list_sessions_router(request):
    sessions = list_active_sessions(request.auth)
    return 200, [SessionOut.from_orm(token) for token in sessions]


@router.delete(
    "/sessions/{session_id}",
    response={200: MessageOut, 404: MessageOut},
    auth=AllRolesAuth(),
    summary="Revoga uma sessão específica",
    description="Blacklista o refresh token correspondente, encerrando aquela sessão/dispositivo.",
)
@ratelimit(key="user", rate="20/h", block=True)
def revoke_session_router(request, session_id: int):
    try:
        revoke_session(user=request.auth, session_id=session_id)
        return 200, {"detail": "Sessão revogada com sucesso."}
    except SessionNotFound as e:
        return 404, {"detail": str(e)}

    

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
        auth=AllRolesAuth(), summary="Alterar senha", description=(
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
    


@router.delete(
    "/delete-account",
    response={200: MessageOut, 400: MessageOut},
    auth=EmployeeOrClientAuth(),
    summary="Exclui a própria conta",
    description=(
        "Exclusão de conta pelo próprio usuário (LGPD — direito de eliminação). "
        "Exige confirmação de senha. Não é um hard-delete: o registro é mantido "
        "para preservar vínculos (agendamentos, pagamentos, etc.), mas todo dado "
        "pessoal do perfil é apagado/anonimizado, a senha se torna inutilizável "
        "e todas as sessões são revogadas imediatamente."
    ),
)
@ratelimit(key="user", rate="5/h", block=True)
def delete_account_router(request, payload: DeleteAccountIn):
    try:
        delete_own_account(user=request.auth, password=payload.password)
        return 200, {"detail": "Conta excluída com sucesso."}
    except InvalidPassword as e:
        return 400, {"detail": str(e)}


@router.get(
    "/export-my-data",
    response={200: dict},
    auth=AllRolesAuth(),
    summary="Exporta os dados pessoais do usuário logado",
    description=(
        "Direito de portabilidade (LGPD): retorna os dados pessoais do usuário "
        "autenticado (conta + perfil) em formato estruturado."
    ),
)
@ratelimit(key="user", rate="10/h", block=True)
def export_my_data_router(request):
    return 200, export_user_data(request.auth.id)





@router.post("/register-employee", response={201: TokenOut, 409: MessageOut}, auth=AdminOnlyAuth(), summary="Cadastro de Funcionário",)
@ratelimit(key="ip", rate="20/h", block=True,)
def register_employee_router(request, payload: RegisterEmployeeIn):
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


@router.post("/reactivate-user/{user_id}", response={201: UserOut, 404: MessageOut, 400: MessageOut}, auth=AdminOnlyAuth(), summary="Reativa Usuário.")
@ratelimit(key="ip", rate="20/h", block=True)
def reactivate_user_router(request, user_id: uuid.UUID):
    try:
        user = reactivate_user(user_id, performed_by=request.auth)
        return 201, UserOut.from_orm(user=user)
    except UserNotFound as e:
        return 404, {"detail": str(e)}
    except Exception as e:
        return 400, {"detail": f"Erro ao reativar usuário: {str(e)}"}


@router.patch("/update-client-profile", response={200: ClientOut, 404: MessageOut, 400: MessageOut}, auth=ClientOnlyAuth(), summary="Atualiza perfil do Cliente logado.")
@ratelimit(key="ip", rate="20/h", block=True)
def update_profile_client_router(request, payload: ClientUpdateIn):
    try:
        user: User = request.auth
        client_updated = update_client_profile(user_id=user.id, payload=payload)
        return 200, client_updated 
    except UserNotFound as e:
        return 404, {"detail": str(e)}
    except Exception as e:
        return 400, {"detail": f"Erro ao atualizar perfil: {str(e)}"}



@router.patch("/update-employee-profile", response={200: EmployeeOut, 404: MessageOut, 400: MessageOut}, auth=EmployeeOnlyAuth(), summary="Atualiza perfil do Funcionário logado.")
@ratelimit(key="ip", rate="20/h", block=True)
def update_profile_employee_router(request, payload: EmployeeUpdateIn):
    try:
        user: User = request.auth
        client_updated = update_employee_profile(user_id=user.id, payload=payload)
        return 200, client_updated 
    except UserNotFound as e:
        return 404, {"detail": str(e)}
    except Exception as e:
        return 400, {"detail": f"Erro ao atualizar perfil: {str(e)}"}


@router.post("/upload-client-photo", response={200: ClientOut, 400: MessageOut, 404: MessageOut}, auth=ClientOnlyAuth(), summary="Upload da foto do Cliente logado.")
@ratelimit(key="user", rate="10/h", block=True)
def upload_client_photo_router(request, photo: UploadedFile = File(...)):
    try:
        user: User = request.auth
        client_updated = upload_client_profile_photo(user=user, photo=photo)
        return 200, client_updated
    except UserNotFound as e:
        return 404, {"detail": str(e)}
    except InvalidImageFile as e:
        return 400, {"detail": str(e)}


@router.delete("/delete-client-photo", response={200: ClientOut, 404: MessageOut}, auth=ClientOnlyAuth(), summary="Remove a foto do Cliente logado (volta para a foto padrão).")
@ratelimit(key="user", rate="10/h", block=True)
def delete_client_photo_router(request):
    try:
        user: User = request.auth
        client_updated = delete_client_profile_photo(user=user)
        return 200, client_updated
    except UserNotFound as e:
        return 404, {"detail": str(e)}


@router.post("/upload-employee-photo", response={200: EmployeeOut, 400: MessageOut, 404: MessageOut}, auth=EmployeeOnlyAuth(), summary="Upload da foto do Funcionário logado.")
@ratelimit(key="user", rate="10/h", block=True)
def upload_employee_photo_router(request, photo: UploadedFile = File(...)):
    try:
        user: User = request.auth
        employee_updated = upload_employee_profile_photo(user=user, photo=photo)
        return 200, employee_updated
    except UserNotFound as e:
        return 404, {"detail": str(e)}
    except InvalidImageFile as e:
        return 400, {"detail": str(e)}


@router.delete("/delete-employee-photo", response={200: EmployeeOut, 404: MessageOut}, auth=EmployeeOnlyAuth(), summary="Remove a foto do Funcionário logado (volta para a foto padrão).")
@ratelimit(key="user", rate="10/h", block=True)
def delete_employee_photo_router(request):
    try:
        user: User = request.auth
        employee_updated = delete_employee_profile_photo(user=user)
        return 200, employee_updated
    except UserNotFound as e:
        return 404, {"detail": str(e)}