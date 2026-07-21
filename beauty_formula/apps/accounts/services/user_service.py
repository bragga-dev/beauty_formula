"""
User Services — criação e atualização de usuário base.
"""
import logging
import uuid

from django.db import transaction
from django.utils import timezone

from ninja_jwt.token_blacklist.models import BlacklistedToken, OutstandingToken

from beauty_formula.apps.accounts.models.client import Client
from beauty_formula.apps.accounts.models.employee import Employee
from beauty_formula.apps.accounts.models.user import User
from beauty_formula.apps.accounts.repositories.client_repository import (
    create_client,
    delete_client,
    remove_client_photo,
    update_client,
)
from beauty_formula.apps.accounts.repositories.employee_repository import (
    create_employee,
    remove_employee_photo,
    update_employee,
)
from beauty_formula.apps.accounts.repositories.user_repository import (
    activate_user,
    create_user,
    delete_user,
)
from beauty_formula.apps.accounts.schemas.me_schema import (
    MeOut,

    )
from beauty_formula.apps.accounts.schemas.user_schema import RegisterIn
from beauty_formula.apps.accounts.schemas.client_schema import ClientUpdateIn, ClientOut
from beauty_formula.apps.accounts.schemas.employee_schema import EmployeeUpdateIn, EmployeeOut
from beauty_formula.apps.accounts.selectors.client_selector import (
    get_client_by_user_id,
)
from beauty_formula.apps.accounts.selectors.user_selector import (
    email_exists,
    get_user_by_email,
    get_user_by_id,
    get_user_confirmed_by_role,
    get_user_with_related,
)
from beauty_formula.apps.accounts.tasks.send_promote_employee import (
    send_promote_employee,
)
from beauty_formula.apps.accounts.tasks.send_verification_email_employee import (
    send_verification_email_employee,
)
from beauty_formula.apps.accounts.tasks.verification_account import (
    send_verification_email,
)
from beauty_formula.apps.core.exceptions.permissions import PermissionDenied
from beauty_formula.apps.core.exceptions.auth import InvalidGoogleToken, InvalidPassword
from beauty_formula.apps.core.exceptions.user import UserAlreadyExists


from beauty_formula.apps.core.exceptions.user import UserNotFound
from beauty_formula.apps.core.oauth.google import verify_google_id_token
from beauty_formula.apps.core.tokens.jwt import make_tokens, revoke_all_tokens
from beauty_formula.apps.core.utils.generate_password import generate_temp_password

logger = logging.getLogger(__name__)



def get_current_user_profile(user_id: uuid.UUID) -> MeOut:
    """
    Monta o retorno de GET /auth/me: usuário autenticado + profile
    correspondente à sua role (client/employee/nenhum, no caso de admin).
    """
    user = get_user_with_related(user_id)
    if not user:
        raise UserNotFound("Usuário não encontrado.")
    return MeOut.from_user(user)


def update_client_profile(user_id: uuid.UUID, payload: ClientUpdateIn) -> ClientOut:
    user = get_user_with_related(user_id)
    if not user:
        raise UserNotFound("Usuário não encontrado.")

    if user.role != User.UserRole.CLIENT:
        raise PermissionDenied("Apenas clientes podem atualizar este perfil.")

    fields = payload.dict(exclude_unset=True)
    updated_client = update_client(client=user.client_profile, **fields)
    return ClientOut.from_orm(updated_client)


def update_employee_profile(user_id: uuid.UUID, payload: EmployeeUpdateIn) -> EmployeeOut:
    user = get_user_with_related(user_id)
    if not user:
        raise UserNotFound("Usuário não encontrado.")

    if user.role != User.UserRole.EMPLOYEE:
        raise PermissionDenied("Apenas funcionários podem atualizar este perfil.")

    fields = payload.dict(exclude_unset=True)
    updated_employee = update_employee(employee=user.employee_profile, **fields)
    return EmployeeOut.from_orm(updated_employee)


@transaction.atomic
def register_user_default_client(data: RegisterIn) -> dict:
    """
    Cria o User + Client e dispara e-mail de verificação.
    Retorna os tokens JWT diretamente para o cliente já poder operar.
    """
    if email_exists(data.email):
        raise UserAlreadyExists("e-mail")
    user = create_user(email=data.email, password=data.password, role=User.UserRole.CLIENT)

    if user.role == User.UserRole.CLIENT:
        create_client(user)

    send_verification_email.delay(user.pk)   
    return make_tokens(user)


@transaction.atomic
def login_or_register_client_google(id_token: str) -> tuple[dict, bool]:
    """
    Login/Cadastro de Cliente via Google (Sign in with Google).

    - Valida o id_token junto ao Google (assinatura, expiração, audience).
    - Se já existe um usuário com o e-mail do token: apenas loga (e ativa
      a conta, caso ainda não estivesse ativa — o Google já garante que
      o e-mail é verificado).
    - Se não existe: cria um Cliente novo, já ativo, sem senha utilizável
      (login exclusivamente via Google até que o usuário defina uma senha).

    Retorna (tokens, created) — created=True quando um novo usuário foi criado,
    útil para o endpoint decidir entre 200 (login) e 201 (cadastro).
    """
    claims = verify_google_id_token(id_token)

    if not claims.get("email_verified", False):
        raise InvalidGoogleToken("E-mail da conta Google não verificado.")

    email = claims["email"]
    user = get_user_by_email(email)
    created = False

    if user is None:
        user = create_user(email=email, password=None, role=User.UserRole.CLIENT)
        create_client(
            user,
            first_name=claims.get("given_name"),
            last_name=claims.get("family_name"),
        )
        created = True

    if not user.is_active or not user.is_trusty:
        user = activate_user(user)

    return make_tokens(user), created


@transaction.atomic
def register_user_default_employee(data: RegisterIn) -> dict:
    """
    Cria o User + Employee e dispara e-mail de verificação.
    Retorna os tokens JWT diretamente para o cliente já poder operar.
    """
    if email_exists(data.email):
        raise UserAlreadyExists("e-mail")
    password = generate_temp_password()
    user = create_user(email=data.email, password=password, role=User.UserRole.EMPLOYEE)

    if user.role == User.UserRole.EMPLOYEE:
        create_employee(user)

    send_verification_email_employee.delay(user.pk, password)
    return make_tokens(user)


@transaction.atomic
def promote_client_to_employee(user_id: uuid.UUID, performed_by=None) -> Employee:
    """
    Promove um client existente para employee: valida que o usuário
    existe e é client, muda a role, remove o profile de Client antigo
    (evita duplicidade/órfão) e cria o profile de Employee.
    Restrito a admin (AdminOnlyAuth na rota).
    """
    role = User.UserRole.CLIENT
    user = get_user_confirmed_by_role(user_id=user_id, role=role)
    if not user or user.role != User.UserRole.CLIENT:
        logger.warning(f"Promoção abortada: cliente {user_id} não encontrado ou não é client")
        raise UserNotFound("Cliente não encontrado ou não é trusty")

    old_client = get_client_by_user_id(user.id)
    if old_client:
        delete_client(old_client)

    user.role = User.UserRole.EMPLOYEE
    user.save(update_fields=["role"])

    employee = create_employee(user)
    send_promote_employee.delay(user.pk)

    return employee



@transaction.atomic
def deactivate_account(user_id: uuid.UUID, performed_by=None, reason="Desativação de conta"):
    """ Desativa usuário, revoga todos os tokens ativos e cria log de auditoria"""
    user = get_user_by_id(user_id)
    if not user:
        logger.warning(f"Desativação abortada: usuário {user_id} não encontrado")
        raise UserNotFound("Usuário não encontrado.")
 
    if not user.is_active:
        logger.warning(f"Desativação abortada: usuário {user_id} já está inativo")
        raise UserNotFound("Usuário já está desativado.")
 
    for token in OutstandingToken.objects.filter(user=user):
        BlacklistedToken.objects.get_or_create(token=token)
 
    user.is_active = False
    user.save(update_fields=["is_active"])
 
    return user


def reactivate_user(user_id: uuid.UUID, performed_by=None) -> User:
    """Contrapartida de deactivate_account: reativa um usuário desativado. Restrito a admin."""
    user = get_user_by_id(user_id)
    if not user:
        logger.warning(f"Reativação abortada: usuário {user_id} não encontrado")
        raise UserNotFound("Usuário não encontrado.")

    if user.is_active:
        logger.warning(f"Reativação abortada: usuário {user_id} já está ativo")
        raise UserNotFound("Usuário já está ativo.")

    return activate_user(user)


@transaction.atomic
def delete_own_account(user: User, password: str) -> None:
    """
    Exclusão definitiva da conta pelo próprio usuário (LGPD — direito de eliminação).
 
    Hard-delete de verdade: apaga o registro de User do banco (o que remove
    em cascata o profile de Client/Employee via OneToOne). Contas admin não
    podem ser excluídas por este endpoint — só via ação administrativa direta.
    """
    if user.role == User.UserRole.ADMIN:
        raise PermissionDenied("Contas de administrador não podem ser excluídas por este endpoint.")
 
    if not user.check_password(password):
        raise InvalidPassword("Senha incorreta. Não foi possível confirmar a exclusão da conta.")
 
    profile = None
    if user.role == User.UserRole.CLIENT:
        profile = getattr(user, "client_profile", None)
    elif user.role == User.UserRole.EMPLOYEE:
        profile = getattr(user, "employee_profile", None)
 
    if profile and profile.photo:
        default_photo = Client.photo.field.default if isinstance(profile, Client) else Employee.photo.field.default
        if profile.photo.name != default_photo:
            profile.photo.delete(save=False)
 
    revoke_all_tokens(user)
    delete_user(user)
 


def export_user_data(user_id: uuid.UUID) -> dict:
    """
    Monta o export dos dados pessoais do usuário (LGPD — direito de portabilidade).
    Cobre os dados do app accounts (conta + perfil). Se/quando existirem dados
    de outros domínios ligados ao usuário (agendamentos, pagamentos, etc.),
    devem ser agregados aqui.
    """
    user = get_user_with_related(user_id)
    if not user:
        raise UserNotFound("Usuário não encontrado.")

    data = {
        "conta": {
            "id": str(user.id),
            "email": user.email,
            "tipo": user.get_role_display(),
            "ativo": user.is_active,
            "confiavel": user.is_trusty,
            "data_cadastro": user.date_joined.isoformat(),
            "criado_em": user.created_at.isoformat(),
            "atualizado_em": user.updated_at.isoformat(),
        },
        "perfil": None,
    }

    profile = None
    if user.role == User.UserRole.CLIENT:
        profile = getattr(user, "client_profile", None)
    elif user.role == User.UserRole.EMPLOYEE:
        profile = getattr(user, "employee_profile", None)

    if profile:
        data["perfil"] = {
            "nome": profile.first_name,
            "sobrenome": profile.last_name,
            "username": profile.username,
            "telefone": str(profile.phone) if profile.phone else None,
            "genero": profile.gender,
            "data_nascimento": profile.birth_date.isoformat() if profile.birth_date else None,
            "instagram": profile.instagram,
            "foto_url": profile.photo_url,
        }
        if hasattr(profile, "bio"):
            data["perfil"]["biografia"] = profile.bio

    data["gerado_em"] = timezone.now().isoformat()
    return data