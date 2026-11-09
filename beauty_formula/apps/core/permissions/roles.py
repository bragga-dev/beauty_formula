
from collections.abc import Iterable
from uuid import UUID

from beauty_formula.apps.accounts.models.user import User
from beauty_formula.apps.accounts.models.employee import Employee
from beauty_formula.apps.accounts.models.client import Client
from beauty_formula.apps.accounts.models.manager import Manager


# ==========================================================
# ROLE CHECKS
# ==========================================================

def is_admin(user: User) -> bool:
    return user.is_superuser or user.role == User.UserRole.ADMIN


def is_manager(user: User) -> bool:
    return user.role == User.UserRole.MANAGER


def is_employee(user: User) -> bool:
    return user.role == User.UserRole.EMPLOYEE


def is_client(user: User) -> bool:
    return user.role == User.UserRole.CLIENT


# ==========================================================
# ACCOUNT STATUS
# ==========================================================

def is_superuser(user: User) -> bool:
    return user.is_superuser


def is_active(user: User) -> bool:
    return user.is_active


def is_trusty(user: User) -> bool:
    return user.is_trusty


def is_verified(user: User) -> bool:
    return is_trusty(user) and is_active(user)


def is_staff(user: User) -> bool:
    return user.is_staff


# ==========================================================
# OWNERSHIP CHECKS
# ==========================================================

def is_owner(user: User, resource_user_id: UUID) -> bool:
    return user.id == resource_user_id


def is_manager_owner(user: User, manager: Manager) -> bool:
    return user.id == manager.user_id


def is_employee_owner(user: User, employee: Employee) -> bool:
    return user.id == employee.user_id


def is_client_owner(user: User, client: Client) -> bool:
    return user.id == client.user_id


# ==========================================================
# ROLE COMPOSITION
# ==========================================================

def has_any_role(user: User, roles: Iterable) -> bool:
    return user.role in roles


# ==========================================================
# BUSINESS PERMISSIONS
# ==========================================================

def can_view_finances(user: User, employee: Employee) -> bool:
    return (
        is_admin(user)
        or is_employee_owner(user, employee)
    )
