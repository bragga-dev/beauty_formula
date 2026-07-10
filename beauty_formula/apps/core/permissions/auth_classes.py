# """
# Auth Classes - Classes de autenticação com permissões embutidas.
# """
# from ninja_jwt.authentication import JWTAuth
# from beauty_formula.apps.core.exceptions import PermissionDenied
# from .roles import is_church, is_member, is_admin, is_active, is_verified
# from ecclesia.apps.users.models.church import Church
# DEFAULT_USER_PHOTO = "default/user_img.jpg"
# DEFAULT_CHURCH_BANNER = "default/banner.jpg"

# class ChurchOnlyAuth(JWTAuth):
#     def authenticate(self, request, token):
#         user = super().authenticate(request, token)
#         if user and not is_verified(user):  # Verificar email PRIMEIRO
#             raise PermissionDenied("Verifique seu e-mail para acessar.")
#         if user and not is_admin(user) and not is_church(user):
#             raise PermissionDenied("Apenas igrejas podem acessar este recurso.")
#         return user

# class ChurchCompleteProfileAuth(JWTAuth):
#     def authenticate(self, request, token):
#         user = super().authenticate(request, token)

#         if not user:
#             return None
#         if not is_admin(user) and not is_church(user):
#             raise PermissionDenied("Apenas igrejas podem acessar este recurso.")
#         try:
#             church = user.church
#         except Church.DoesNotExist:
#             raise PermissionDenied("Usuário não possui igreja vinculada.")

#         required_fields = {
#             "Nome completo": church.full_name,
#             "CNPJ": church.cnpj,
#             "Telefone": church.phone,
#             "Banner": church.banner,
#             "Descrição": church.about,
#             "Foto": church.user.photo,
#             "Instagram": church.instagram,
#         }

#         missing = [field for field, value in required_fields.items() if not value]

#         if church.user.photo == DEFAULT_USER_PHOTO:
#             missing.append("Foto (não pode ser a foto padrão)")

#         if church.banner == DEFAULT_CHURCH_BANNER:
#             missing.append("Banner (não pode ser a banner padrão)")

#         if missing:
#             missing_count = len(missing)
#             fields_list = ', '.join(missing)
            
#             raise PermissionDenied(
#                 f"Complete seu perfil antes de executar essa ação. "
#                 f"{missing_count} campo(s) obrigatório(s) faltando: {fields_list}"
#             )

#         if not church.is_verified:
#             raise PermissionDenied("A igreja precisa ser verificada para acessar.")
#         return user


# class MemberOnlyAuth(JWTAuth):
#     def authenticate(self, request, token):
#         user = super().authenticate(request, token)
#         if user and not is_admin(user) and not is_verified(user):  # Verificar email PRIMEIRO
#             raise PermissionDenied("Verifique seu e-mail para acessar.")
#         if user and not is_admin(user) and not is_member(user):
#             raise PermissionDenied("Apenas membros podem acessar este recurso.")
#         return user


# class AdminOnlyAuth(JWTAuth):
#     def authenticate(self, request, token):
#         user = super().authenticate(request, token)
#         if user and not is_admin(user):
#             raise PermissionDenied("Apenas administradores podem acessar este recurso.")
#         return user


# class ActiveUserAuth(JWTAuth):
#     def authenticate(self, request, token):
#         user = super().authenticate(request, token)
#         if user and not is_active(user):
#             raise PermissionDenied("Sua conta não está ativa.")
#         return user


# class VerifiedUserAuth(JWTAuth):
#     def authenticate(self, request, token):
#         user = super().authenticate(request, token)
#         if user and not is_admin(user) and not is_verified(user):
#             raise PermissionDenied("Verifique seu e-mail para acessar.")
#         return user