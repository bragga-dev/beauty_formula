"""
User Services — criação e atualização de usuário base.
"""
from beauty_formula.apps.accounts.models.user import User
from beauty_formula.apps.accounts.repositories.user_repository import create_user
from beauty_formula.apps.accounts.repositories.employee_repository import create_employee
from beauty_formula.apps.accounts.repositories.client_repository import create_client
from beauty_formula.apps.core.exceptions import UserAlreadyExists
from beauty_formula.apps.accounts.selectors.user_selector import email_exists
from beauty_formula.apps.accounts.schemas.user_schema import RegisterIn
from django.db import transaction
from ninja_jwt.token_blacklist.models import OutstandingToken, BlacklistedToken
from django.db import transaction
from django.utils import timezone
from beauty_formula.apps.core.models.audit_user_model import AuditLog 
from beauty_formula.apps.accounts.tasks.verification_account import send_verification_email
from beauty_formula.apps.core.tokens.jwt import make_tokens




def register_user(data: RegisterIn) -> dict:
    """
    Cria o User + perfil (Church ou Member) e dispara e-mail de verificação.
    Retorna os tokens JWT diretamente para o cliente já poder operar.
    """
    if email_exists(data.email):
        raise UserAlreadyExists("e-mail")
    user = create_user(email=data.email, password=data.password, role=data.role,)

    if user.role == User.UserRole.EMPLOYEE:
        create_employee(user)
    if user.role == User.UserRole.CLIENT:
        create_client(user)

    send_verification_email.delay(user.pk)   
    return make_tokens(user)


@transaction.atomic
def deactivate_account(user, performed_by=None, reason="Desativação de conta"):
    """ Desativa usuário, revoga todos os tokens ativos e cria logger de auditória"""
    for token in OutstandingToken.objects.filter(user=user):
        BlacklistedToken.objects.get_or_create(token=token)
    user.is_active = False
    user.save(update_fields=["is_active"])
    AuditLog.objects.create(
        action="DEACTIVATE_ACCOUNT",
        user=user,
        performed_by=performed_by,  
        reason=reason,
        timestamp=timezone.now(),
        details={
            "tokens_revoked": True,
            "user_id": str(user.id),
            "email": user.email,
        }
    )