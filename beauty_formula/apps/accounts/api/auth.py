"""
Login endpoint — autenticação de usuários.
"""
from ninja import Router
from ninja_jwt.authentication import JWTAuth
from beauty_formula.apps.accounts.services.auth_service import  (
    login_user,
    logout_user,
    refresh_access_token,
    change_password,
    request_password_reset,
    confirm_password_reset,    
    
)

from beauty_formula.apps.accounts.services.user_service import  (
  register_user,
  deactivate_account,    
)

from beauty_formula.apps.accounts.schemas.user_schema import (
    LoginIn,
    TokenOut,
    MessageOut,
    RefreshIn,
    ChangePasswordIn,
    PasswordResetRequestIn,
    PasswordResetConfirmIn,
    RegisterIn,
    
)
from beauty_formula.apps.core.exceptions import InvalidCredentials, EmailNotVerified, InvalidPassword, InvalidToken, UserAlreadyExists
from django_ratelimit.decorators import ratelimit

router = Router()

 

@router.post("/login", response={200: TokenOut, 401: MessageOut, 403: MessageOut}, auth=None, summary="Login")
@ratelimit(key="ip", rate="5/m", block=True)
def login(request, payload: LoginIn):
    try:
        tokens = login_user(payload.email, payload.password)
        return 200, tokens
    except EmailNotVerified:
        return 403, {"detail": "E-mail não verificado."}
    except InvalidCredentials:
        return 401, {"detail": "E-mail ou senha inválidos."}
    


@router.post("/logout", response={200: MessageOut, 401: MessageOut},  auth=JWTAuth(), summary="Logout (blacklista o refresh token)",)
@ratelimit(key="user", rate="30/m", block=True)
def logout(request, payload: RefreshIn):
    try:
        logout_user(payload.refresh)
        return 200, {"detail": "Logout realizado com sucesso."}
    except InvalidToken as e:
        return 401, {"detail": str(e)}
    

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
    


@router.post("/password-reset/request", response={200: MessageOut}, auth=None, summary="Solicitar reset de senha",)
@ratelimit(key="ip", rate="3/h", block=True,)
def password_reset_request(request, payload: PasswordResetRequestIn):
    request_password_reset(payload.email)
    return 200, {"detail": "Se este e-mail estiver cadastrado, você receberá as instruções em breve."}


@router.post("/password-reset/confirm", response={200: MessageOut, 400: MessageOut},  auth=None, summary="Confirmar reset de senha",)
@ratelimit(key="ip", rate="30/h",  block=True,)
def password_reset_confirm(request, payload: PasswordResetConfirmIn):
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
def refresh(request, payload: RefreshIn):
    try:
        data = refresh_access_token(payload.refresh)
        return 200, data
    except InvalidToken as e:
        return 401, {"detail": str(e)}
    


@router.post("/register", response={201: TokenOut, 409: MessageOut}, auth=None, summary="Cadastro de Igreja ou Membro",)
@ratelimit(key="ip", rate="5/h", block=True,)
def register(request, payload: RegisterIn):
    """
    Cria o usuário, o perfil (Church ou Member) e retorna tokens JWT.
    Um e-mail de verificação é enviado em background via Celery.
    """
    try:
        tokens = register_user(payload)
        return 201, tokens
    except UserAlreadyExists as e:
        return 409, {"detail": str(e)}