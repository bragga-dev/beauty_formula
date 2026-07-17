"""
Auth Classes - Classes de autenticação com permissões embutidas.
"""
from ninja_jwt.authentication import JWTAuth
from beauty_formula.apps.core.exceptions import PermissionDenied
from beauty_formula.apps.core.permissions.roles import is_employee, is_client, is_admin, is_active, is_verified
from beauty_formula.apps.accounts.models.employee import Employee

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
            employee = user.employee
            client = user.client
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