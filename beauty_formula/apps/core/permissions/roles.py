"""
Roles - Funções que verificam o tipo e estado do usuário.
"""
from beauty_formula.apps.accounts.models.user import User

# ═══════════════════════════════════════════════════════════════════════════════
# Verificações de Role (tipo de usuário)
# ═══════════════════════════════════════════════════════════════════════════════

def is_employee(user: User) -> bool:
    """Verifica se o usuário é uma Funcionário."""
    return user.role == User.UserRole.EMPLOYEE


def is_client(user: User) -> bool:
    """Verifica se o usuário é um Cliente."""
    return user.role == User.UserRole.CLIENT


def is_admin(user: User) -> bool:
    """
    Verifica se o usuário é ADMIN (superuser ou role admin).
    ADMINS têm poderes especiais e bypass em várias verificações.
    """
    return user.is_superuser or user.role == User.UserRole.ADMIN


def is_superuser(user: User) -> bool:
    """Verifica se o usuário é superuser (root do sistema)."""
    return user.is_superuser


# ═══════════════════════════════════════════════════════════════════════════════
# Verificações de Estado
# ═══════════════════════════════════════════════════════════════════════════════

def is_active(user: User) -> bool:
    """Verifica se o usuário está ativo (conta aprovada/ativada)."""
    return user.is_active


def is_trusty(user: User) -> bool:
    """Verifica se o usuário é confiável (email verificado)."""
    return user.is_trusty


def is_verified(user: User) -> bool:
    """
    Verifica se o usuário é confiável E ativo.
    Combinação usada para acesso completo ao sistema.
    """
    return user.is_trusty and user.is_active


def is_staff(user: User) -> bool:
    """Verifica se o usuário é staff (acesso ao admin Django)."""
    return user.is_staff


# ═══════════════════════════════════════════════════════════════════════════════
# Verificações de Ownership (dono do recurso)
# ═══════════════════════════════════════════════════════════════════════════════

def is_owner(user: User, resource_user_id) -> bool:
    """Verifica se o usuário é o dono do recurso (pelo user_id)."""
    return str(user.id) == str(resource_user_id)


def is_employee_owner(user: User, employee) -> bool:
    """Verifica se o usuário é o dono de um recurso da Barbearia."""
    return user == employee.user


def is_client_owner(user: User, client) -> bool:
    """Verifica se o usuário é o dono de um recurso da Barbearia."""
    return user == client.user


# ═══════════════════════════════════════════════════════════════════════════════
# Combinadores
# ═══════════════════════════════════════════════════════════════════════════════

def has_any_role(user: User, roles: list) -> bool:
    """Verifica se o usuário tem alguma das roles especificadas."""
    return user.role in roles


def has_all_roles(user: User, roles: list) -> bool:
    """Verifica se o usuário tem todas as roles especificadas."""
    return all(user.role == role for role in roles)




def can_view_finances(user: User, employee) -> bool:
    """
    Verifica se o usuário pode ver finanças da Barbearia.
    
    Quem pode:
    - Admin do sistema
    - Dono da funcionário
    - Pastor
    - Tesoureiro
    - Administrador da funcionário
    """
    return (
        is_admin(user) or
        is_employee_owner(user, employee) 
    )