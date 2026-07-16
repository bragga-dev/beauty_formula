"""
User Services — criação e atualização de usuário base.
"""
import uuid
from beauty_formula.apps.accounts.models.user import User
from beauty_formula.apps.accounts.repositories.user_repository import create_user
from beauty_formula.apps.accounts.repositories.employee_repository import create_employee
from beauty_formula.apps.accounts.repositories.client_repository import create_client
from beauty_formula.apps.core.exceptions import UserAlreadyExists
from beauty_formula.apps.accounts.selectors.user_selector import email_exists, get_user_by_id, get_user_confirmed_by_role
from beauty_formula.apps.accounts.schemas.user_schema import RegisterIn
from django.db import transaction
from ninja_jwt.token_blacklist.models import OutstandingToken, BlacklistedToken
from django.db import transaction
from django.utils import timezone
from beauty_formula.apps.core.models.audit_user_model import AuditLog 
from beauty_formula.apps.accounts.tasks.verification_account import send_verification_email
from beauty_formula.apps.accounts.tasks.send_verification_email_employee import send_verification_email_employee
from beauty_formula.apps.core.tokens.jwt import make_tokens
from beauty_formula.apps.core.utils.generate_password import generate_temp_password
from beauty_formula.apps.core.exceptions.user import UserNotFound
from beauty_formula.apps.accounts.models.employee import Employee
from beauty_formula.apps.accounts.tasks.send_promote_employee import send_promote_employee
import logging
logger = logging.getLogger(__name__)

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
    existe e é client, muda a role, salva e cria o profile de Employee.
    Restrito a admin (AdminOnlyAuth na rota).
    """
    role = User.UserRole.CLIENT
    user = get_user_confirmed_by_role(user_id=user_id, role=role)
    if not user or user.role != User.UserRole.CLIENT:
        logger.warning(f"Promoção abortada: cliente {user_id} não encontrado ou não é client")
        raise UserNotFound("Cliente não encontrado ou não é trusty")

    user.role = User.UserRole.EMPLOYEE
    user.save(update_fields=["role"])

    employee = create_employee(user)
    send_promote_employee.delay(user.pk)

    return employee



transaction.atomic
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
