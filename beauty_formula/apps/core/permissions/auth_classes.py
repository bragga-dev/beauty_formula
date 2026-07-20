"""
Auth Classes - Classes de autenticação com permissões embutidas.
"""
from ninja_jwt.authentication import JWTAuth
from beauty_formula.apps.core.exceptions import PermissionDenied
from beauty_formula.apps.core.permissions.roles import (
    has_any_role,
    is_admin,
    is_active,
    is_client,
    is_employee,
    is_verified,
)
from beauty_formula.apps.accounts.models.employee import Employee
from beauty_formula.apps.accounts.models.user import User

DEFAULT_EMPLOYEE_PHOTO = "default/employee_img.jpeg"
DEFAULT_CLIENT_PHOTO = "default/client_img.jpg"



class EmployeeOnlyAuth(JWTAuth):
    def authenticate(self, request, token):
        user = super().authenticate(request, token)
        if user and not is_verified(user):  
            raise PermissionDenied("Verifique seu e-mail para acessar.")
        if user and not is_admin(user) and not is_employee(user):
            raise PermissionDenied("Apenas funcionários podem acessar este recurso.")
        return user

class EmployeeCompleteProfileAuth(JWTAuth):
    def authenticate(self, request, token):
        user = super().authenticate(request, token)

        if not user:
            return None
        if not is_admin(user) and not is_employee(user):
            raise PermissionDenied("Apenas funcionários podem acessar este recurso.")
        try:
            employee = user.employee_profile
            client = user.client_profile
        except Employee.DoesNotExist:
            raise PermissionDenied("Usuário não possui funcionário vinculada.")

        required_fields = {
            "Nome completo": employee.full_name,
            "CNPJ": employee.cnpj,
            "Telefone": employee.phone,
            "Banner": employee.banner,
            "Descrição": employee.about,
            "Foto": employee.user.photo,
            "Instagram": employee.instagram,
        }

        missing = [field for field, value in required_fields.items() if not value]

        if employee.photo == DEFAULT_CLIENT_PHOTO:
            missing.append("Foto (não pode ser a foto padrão)")

        if client.photo == DEFAULT_EMPLOYEE_PHOTO:
            missing.append("Foto (não pode ser a foto padrão)")

        if missing:
            missing_count = len(missing)
            fields_list = ', '.join(missing)
            
            raise PermissionDenied(
                f"Complete seu perfil antes de executar essa ação. "
                f"{missing_count} campo(s) obrigatório(s) faltando: {fields_list}"
            )

        if not employee.is_verified:
            raise PermissionDenied("A funcionário precisa ser verificada para acessar.")
        return user


class ClientOnlyAuth(JWTAuth):
    def authenticate(self, request, token):
        user = super().authenticate(request, token)
        if user and not is_admin(user) and not is_verified(user):  
            raise PermissionDenied("Verifique seu e-mail para acessar.")
        if user and not is_admin(user) and not is_client(user):
            raise PermissionDenied("Apenas clients podem acessar este recurso.")
        return user


class AdminOnlyAuth(JWTAuth):
    def authenticate(self, request, token):
        user = super().authenticate(request, token)
        if user and not is_admin(user):
            raise PermissionDenied("Apenas administradores podem acessar este recurso.")
        return user


class ActiveUserAuth(JWTAuth):
    def authenticate(self, request, token):
        user = super().authenticate(request, token)
        if user and not is_active(user):
            raise PermissionDenied("Sua conta não está ativa.")
        return user


class VerifiedUserAuth(JWTAuth):
    def authenticate(self, request, token):
        user = super().authenticate(request, token)
        if user and not is_admin(user) and not is_verified(user):
            raise PermissionDenied("Verifique seu e-mail para acessar.")
        return user


# ═══════════════════════════════════════════════════════════════════════════════
# Classes conjuntas (combinações de roles)
# ═══════════════════════════════════════════════════════════════════════════════

class _CombinedRoleAuth(JWTAuth):
    """
    Base para autenticação que libera acesso a uma combinação de roles.

    Subclasses definem:
      - allowed_roles: lista de User.UserRole permitidas
      - denied_message: mensagem retornada quando a role não está na lista

    Se ADMIN estiver entre as roles permitidas, o admin fica dispensado da
    checagem de e-mail verificado (mesmo comportamento de ClientOnlyAuth /
    AdminOnlyAuth já existentes). Se ADMIN não estiver na lista, ele é
    tratado como qualquer outra role fora da lista: acesso negado.
    """
    allowed_roles: list = []
    denied_message: str = "Você não tem permissão para acessar este recurso."

    def authenticate(self, request, token):
        user = super().authenticate(request, token)
        if not user:
            return None

        admin_is_allowed = User.UserRole.ADMIN in self.allowed_roles
        if not (admin_is_allowed and is_admin(user)) and not is_verified(user):
            raise PermissionDenied("Verifique seu e-mail para acessar.")

        if not has_any_role(user, self.allowed_roles):
            raise PermissionDenied(self.denied_message)

        return user


class AllRolesAuth(_CombinedRoleAuth):
    """Libera acesso para qualquer usuário autenticado e verificado: admin, client ou employee."""
    allowed_roles = [User.UserRole.ADMIN, User.UserRole.CLIENT, User.UserRole.EMPLOYEE]
    denied_message = "Acesso não permitido para este tipo de usuário."


class AdminOrClientAuth(_CombinedRoleAuth):
    """Libera acesso apenas para administradores e clientes (funcionários NÃO passam)."""
    allowed_roles = [User.UserRole.ADMIN, User.UserRole.CLIENT]
    denied_message = "Apenas administradores ou clientes podem acessar este recurso."


class AdminOrEmployeeAuth(_CombinedRoleAuth):
    """Libera acesso apenas para administradores e funcionários (clientes NÃO passam)."""
    allowed_roles = [User.UserRole.ADMIN, User.UserRole.EMPLOYEE]
    denied_message = "Apenas administradores ou funcionários podem acessar este recurso."


class EmployeeOrClientAuth(_CombinedRoleAuth):
    """Libera acesso apenas para funcionários e clientes. Administradores NÃO passam aqui."""
    allowed_roles = [User.UserRole.CLIENT, User.UserRole.EMPLOYEE]
    denied_message = "Apenas funcionários ou clientes podem acessar este recurso."