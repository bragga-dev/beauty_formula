"""
Guards - Funções que bloqueiam ou permitem acesso.
"""
from beauty_formula.apps.core.exceptions.permissions import PermissionDenied

from beauty_formula.apps.core.permissions.roles import is_admin, is_active, is_verified


def check_permission(user, *checks, message: str = None) -> None:
    """
    Verifica se o usuário atende a TODAS as condições.
    
    Args:
        user: Usuário autenticado
        *checks: Funções de verificação (is_employee, is_client, etc.)
        message: Mensagem personalizada de erro
    
    Raises:
        PermissionDenied: Se alguma verificação falhar
    
    Exemplos:
        check_permission(user, is_employee)
        check_permission(user, is_client, is_verified)
    """
    # Admin bypass - superusuário tem acesso total
    if is_admin(user):
        return
    
    for check in checks:
        if not check(user):
            raise PermissionDenied(message)


def check_employee_permission(user, employee, *checks, message: str = None) -> None:
    """
    Verifica permissões que envolvem uma funcionário específico.
    
    Args:
        user: Usuário autenticado
        employee: Instância da Funcioonário
        *checks: Funções que recebem (user, employee)
        message: Mensagem personalizada de erro
    """
    if is_admin(user):
        return
    
    for check in checks:
        if not check(user, employee):
            raise PermissionDenied(message)


def require_active(user) -> None:
    """Requer que o usuário esteja ativo."""
    if is_admin(user):
        return
    if not is_active(user):
        raise PermissionDenied("Sua conta não está ativa. Verifique seu e-mail.")


def require_verified(user) -> None:
    """Requer que o usuário seja verificado (trusty + active)."""
    if not is_verified(user):
        raise PermissionDenied(
            "Verifique seu e-mail antes de continuar. "
            "Verifique sua caixa de spam ou solicite um novo link."
        )

def require_role(role):
    """Requer uma role específica"""
    role_value = role.value if hasattr(role, 'value') else role
    def decorator(user):
        if not is_admin(user):
            user_role_value = user.role.value if hasattr(user.role, 'value') else user.role
            if user_role_value != role_value:
                raise PermissionDenied(f"Acesso restrito a {role_value}s.")
        return True
    return decorator


# Criando verificadores específicos
require_employee = require_role("employee")
require_client = require_role("client")
require_admin = require_role("admin")