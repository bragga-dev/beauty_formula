from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _
from ninja_jwt.token_blacklist.models import BlacklistedToken, OutstandingToken

from beauty_formula.apps.accounts.admin.client_admin import ClientInline
from beauty_formula.apps.accounts.admin.employee_admin import EmployeeInline
from beauty_formula.apps.accounts.admin.forms import UserChangeForm, UserCreationForm
from beauty_formula.apps.accounts.admin.mixins import ExportCsvMixin, bool_icon, role_badge
from beauty_formula.apps.accounts.models import User
from beauty_formula.apps.core.models.audit_user_model import AuditLog


@admin.register(User)
class UserAdmin(ExportCsvMixin, BaseUserAdmin):
    add_form = UserCreationForm
    form = UserChangeForm
    model = User
    inlines = [ClientInline, EmployeeInline]

    csv_export_fields = ("id", "email", "role", "is_active", "is_trusty", "date_joined")

    # ── Listagem ────────────────────────────────────────────────────────────

    list_display = (
        "email",
        "role_display",
        "is_active_display",
        "is_staff_display",
        "is_trusty_display",
        "date_joined",
    )
    list_display_links = ("email",)
    list_filter = ("role", "is_active", "is_staff", "is_superuser", "is_trusty")
    search_fields = ("email",)
    ordering = ("-date_joined",)
    date_hierarchy = "date_joined"
    list_per_page = 25
    readonly_fields = ("id", "last_login", "date_joined", "created_at", "updated_at")
    filter_horizontal = ("groups", "user_permissions")

    fieldsets = (
        (None, {"fields": ("email", "password")}),
        (_("Tipo de conta"), {"fields": ("role", "is_trusty")}),
        (_("Permissões"), {
            "fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions"),
        }),
        (_("Datas importantes"), {"fields": ("last_login", "date_joined", "created_at", "updated_at")}),
        (_("Identificação"), {"fields": ("id",)}),
    )

    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("email", "role", "password1", "password2", "is_staff", "is_active"),
        }),
    )

    actions = [
        "activate_users",
        "deactivate_users",
        "mark_as_trusty",
        "unmark_as_trusty",
        "export_as_csv",
    ]

    # ── Colunas customizadas (badges/ícones) ──────────────────────────────

    @admin.display(description=_("Tipo"), ordering="role")
    def role_display(self, obj):
        return role_badge(obj.role)

    @admin.display(description=_("Ativo"), ordering="is_active")
    def is_active_display(self, obj):
        return bool_icon(obj.is_active, "Ativo", "Inativo")

    @admin.display(description=_("Staff"), ordering="is_staff")
    def is_staff_display(self, obj):
        return bool_icon(obj.is_staff, "Staff", "—")

    @admin.display(description=_("Confiável"), ordering="is_trusty")
    def is_trusty_display(self, obj):
        return bool_icon(obj.is_trusty, "⭐ Confiável", "—")

    # ── Actions ────────────────────────────────────────────────────────────

    @admin.action(description="✅ Ativar usuários selecionados")
    def activate_users(self, request, queryset):
        updated = 0
        for user in queryset.filter(is_active=False):
            user.is_active = True
            user.save(update_fields=["is_active"])
            AuditLog.objects.create(
                user=user,
                action="activate_account",
                performed_by=request.user if request.user.is_authenticated else None,
                reason="Ativado via Django Admin",
            )
            updated += 1
        self.message_user(request, f"{updated} usuário(s) ativado(s) com sucesso.")

    @admin.action(description="🚫 Desativar usuários selecionados")
    def deactivate_users(self, request, queryset):
        updated = 0
        for user in queryset.filter(is_active=True):
            for token in OutstandingToken.objects.filter(user=user):
                BlacklistedToken.objects.get_or_create(token=token)
            user.is_active = False
            user.save(update_fields=["is_active"])
            AuditLog.objects.create(
                user=user,
                action="deactivate_account",
                performed_by=request.user if request.user.is_authenticated else None,
                reason="Desativado via Django Admin",
            )
            updated += 1
        self.message_user(request, f"{updated} usuário(s) desativado(s) e tokens revogados.")

    @admin.action(description="⭐ Marcar como confiável")
    def mark_as_trusty(self, request, queryset):
        updated = queryset.update(is_trusty=True)
        self.message_user(request, f"{updated} usuário(s) marcado(s) como confiável.")

    @admin.action(description="◻️ Remover marcação de confiável")
    def unmark_as_trusty(self, request, queryset):
        updated = queryset.update(is_trusty=False)
        self.message_user(request, f"{updated} usuário(s) tiveram a marcação de confiável removida.")