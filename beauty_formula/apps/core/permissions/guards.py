"""
Guards - Funções que bloqueiam ou permitem acesso.
"""
from typing import Callable, List, Any, Optional, Union
from functools import wraps

from beauty_formula.apps.accounts.schemas.user_schema import UserRoleEnum  
from beauty_formula.apps.core.exceptions.permissions import PermissionDenied
from beauty_formula.apps.core.permissions.roles import (
    is_admin, 
    is_active, 
    is_verified,
    is_employee,
    is_client,
    is_employee_owner,
    is_client_owner,
    is_staff,
)


# ═══════════════════════════════════════════════════════════════════════════════
# Guards Base
# ═══════════════════════════════════════════════════════════════════════════════

def check_permission(
    user, 
    *checks: Callable, 
    message: Optional[str] = None,
    allow_admin_bypass: bool = True
) -> None:
    """
    Verifica se o usuário atende a TODAS as condições.
    
    Args:
        user: Usuário autenticado
        *checks: Funções de verificação que recebem (user)
        message: Mensagem personalizada de erro
        allow_admin_bypass: Se True, admin passa direto
    
    Raises:
        PermissionDenied: Se alguma verificação falhar
    
    Exemplos:
        check_permission(user, is_employee)
        check_permission(user, is_client, is_verified)
        check_permission(user, is_employee, message="Apenas funcionários")
    """
    # Admin bypass - superusuário tem acesso total
    if allow_admin_bypass and is_admin(user):
        return
    
    for check in checks:
        if not check(user):
            raise PermissionDenied(
                message or f"Permissão negada: {check.__name__} falhou."
            )


def check_object_permission(
    user,
    obj: Any,
    *checks: Callable,
    message: Optional[str] = None,
    allow_admin_bypass: bool = True
) -> None:
    """
    Verifica permissões que envolvem um objeto específico.
    
    Args:
        user: Usuário autenticado
        obj: Objeto a ser verificado (Employee, Client, etc.)
        *checks: Funções que recebem (user, obj)
        message: Mensagem personalizada de erro
    
    Exemplos:
        check_object_permission(user, employee, is_employee_owner)
        check_object_permission(user, client, is_client_owner, is_verified)
    """
    if allow_admin_bypass and is_admin(user):
        return
    
    for check in checks:
        if not check(user, obj):
            raise PermissionDenied(
                message or f"Permissão negada: {check.__name__} falhou."
            )


# ═══════════════════════════════════════════════════════════════════════════════
# Guards Específicos
# ═══════════════════════════════════════════════════════════════════════════════

def require_active(user) -> None:
    """
    Requer que o usuário esteja ativo.
    
    Args:
        user: Usuário autenticado
    
    Raises:
        PermissionDenied: Se o usuário não estiver ativo
    """
    if is_admin(user):
        return
    
    if not is_active(user):
        raise PermissionDenied(
            "Sua conta não está ativa. Verifique seu e-mail ou contate o suporte."
        )


def require_verified(user) -> None:
    """
    Requer que o usuário seja verificado (trusty + active).
    
    Args:
        user: Usuário autenticado
    
    Raises:
        PermissionDenied: Se o usuário não for verificado
    """
    if is_admin(user):
        return
    
    if not is_verified(user):
        raise PermissionDenied(
            "Verifique seu e-mail antes de continuar. "
            "Verifique sua caixa de spam ou solicite um novo link de verificação."
        )


def require_staff(user) -> None:
    """
    Requer que o usuário seja staff (acesso ao admin Django).
    
    Args:
        user: Usuário autenticado
    
    Raises:
        PermissionDenied: Se o usuário não for staff
    """
    if is_admin(user):
        return
    
    if not is_staff(user):
        raise PermissionDenied("Acesso restrito à equipe administrativa.")


def require_employee_or_admin(user) -> None:
    """
    Requer que o usuário seja funcionário OU admin.
    
    Args:
        user: Usuário autenticado
    
    Raises:
        PermissionDenied: Se não for funcionário nem admin
    """
    if is_admin(user):
        return
    
    if not is_employee(user):
        raise PermissionDenied("Acesso restrito a funcionários.")


def require_client_or_admin(user) -> None:
    """
    Requer que o usuário seja cliente OU admin.
    
    Args:
        user: Usuário autenticado
    
    Raises:
        PermissionDenied: Se não for cliente nem admin
    """
    if is_admin(user):
        return
    
    if not is_client(user):
        raise PermissionDenied("Acesso restrito a clientes.")


# ═══════════════════════════════════════════════════════════════════════════════
# Factory de Guards
# ═══════════════════════════════════════════════════════════════════════════════

def require_role(role: Union[str, 'UserRoleEnum'], custom_message: Optional[str] = None):
    """
    Factory que cria guards para roles específicas.
    
    Args:
        role: Role requerida (string ou Enum)
        custom_message: Mensagem personalizada de erro
    
    Returns:
        Callable: Guard function
    
    Exemplos:
        require_employee = require_role("employee")
        require_admin = require_role("admin", "Apenas administradores")
    """
    role_value = role.value if hasattr(role, 'value') else str(role)
    
    def guard(user) -> None:
        if is_admin(user):
            return
        
        user_role_value = user.role.value if hasattr(user.role, 'value') else str(user.role)
        
        if user_role_value != role_value:
            raise PermissionDenied(
                custom_message or f"Acesso restrito a {role_value}s."
            )
    
    return guard


# Criando verificadores específicos
require_employee = require_role("employee")
require_client = require_role("client")
require_admin = require_role("admin")


# ═══════════════════════════════════════════════════════════════════════════════
# Decorators para Views
# ═══════════════════════════════════════════════════════════════════════════════

def guard(guard_func: Callable):
    """
    Decorator para aplicar guards em views.
    
    Args:
        guard_func: Função guard que recebe user
    
    Returns:
        Decorated view
    
    Exemplos:
        @guard(require_employee)
        def my_view(request):
            ...
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            guard_func(request.user)
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


def guard_multiple(*guards: Callable):
    """
    Decorator para aplicar múltiplos guards em views.
    
    Args:
        *guards: Funções guard
    
    Returns:
        Decorated view
    
    Exemplos:
        @guard_multiple(require_active, require_employee)
        def my_view(request):
            ...
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            for guard_func in guards:
                guard_func(request.user)
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


# ═══════════════════════════════════════════════════════════════════════════════
# Guards Compostos
# ═══════════════════════════════════════════════════════════════════════════════

def require_owner_or_admin(user, obj, owner_check: Callable) -> None:
    """
    Requer que o usuário seja admin OU dono do objeto.
    
    Args:
        user: Usuário autenticado
        obj: Objeto (Employee, Client, etc.)
        owner_check: Função que verifica ownership (ex: is_employee_owner)
    
    Raises:
        PermissionDenied: Se não for admin nem dono
    """
    if is_admin(user):
        return
    
    if not owner_check(user, obj):
        raise PermissionDenied("Você não tem permissão para acessar este recurso.")


def require_verified_employee(user) -> None:
    """
    Requer que o usuário seja funcionário verificado.
    """
    check_permission(user, is_employee, is_verified, message="Acesso restrito a funcionários verificados.")


def require_verified_client(user) -> None:
    """
    Requer que o usuário seja cliente verificado.
    """
    check_permission(user, is_client, is_verified, message="Acesso restrito a clientes verificados.")


# ═══════════════════════════════════════════════════════════════════════════════
# Guards para API (Ninja)
# ═══════════════════════════════════════════════════════════════════════════════

def api_guard(guard_func: Callable):
    """
    Decorator para aplicar guards em endpoints Ninja.
    
    Exemplos:
        @api_guard(require_employee)
        @api.get("/employee-only")
        def employee_endpoint(request):
            ...
    """
    def decorator(func):
        @wraps(func)
        def wrapper(request, *args, **kwargs):
            guard_func(request.user)
            return func(request, *args, **kwargs)
        return wrapper
    return decorator


__all__ = [
    # Guards base
    "check_permission",
    "check_object_permission",
    
    # Guards específicos
    "require_active",
    "require_verified",
    "require_staff",
    "require_employee_or_admin",
    "require_client_or_admin",
    
    # Factory e verificadores
    "require_role",
    "require_employee",
    "require_client",
    "require_admin",
    
    # Decorators
    "guard",
    "guard_multiple",
    "api_guard",
    
    # Guards compostos
    "require_owner_or_admin",
    "require_verified_employee",
    "require_verified_client",
]