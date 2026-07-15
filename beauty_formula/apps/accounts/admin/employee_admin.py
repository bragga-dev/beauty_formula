from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from beauty_formula.apps.accounts.admin.mixins import (
    ExportCsvMixin,
    gender_badge,
    thumbnail,
)
from beauty_formula.apps.accounts.models import Employee


# ── Inline (usado dentro do UserAdmin) ────────────────────────────────────────

class EmployeeInline(admin.StackedInline):
    model = Employee
    extra = 0
    max_num = 1
    can_delete = False
    verbose_name = _("Perfil de Funcionário")
    verbose_name_plural = _("Perfil de Funcionário")
    fk_name = "user"
    fields = (
        ("first_name", "last_name", "username"),
        ("phone", "gender", "birth_date"),
        "instagram",
        "bio",
        "photo",
    )


# ── Filtro customizado: possui biografia preenchida? ──────────────────────────

class HasBioFilter(admin.SimpleListFilter):
    title = _("biografia")
    parameter_name = "tem_bio"

    def lookups(self, request, model_admin):
        return (
            ("yes", "Preenchida"),
            ("no", "Vazia"),
        )

    def queryset(self, request, queryset):
        value = self.value()
        if value == "yes":
            return queryset.exclude(bio__isnull=True).exclude(bio__exact="")
        if value == "no":
            return queryset.filter(bio__isnull=True) | queryset.filter(bio__exact="")
        return queryset


# ── ModelAdmin ─────────────────────────────────────────────────────────────────

@admin.register(Employee)
class EmployeeAdmin(ExportCsvMixin, admin.ModelAdmin):
    csv_export_fields = ("id", "first_name", "last_name", "phone", "gender", "birth_date")

    list_display = (
        "avatar",
        "full_name",
        "user_email",
        "phone",
        "gender_display",
        "birth_date",
        "is_user_active",
    )
    list_display_links = ("full_name",)
    list_filter = ("gender", HasBioFilter, "user__is_active")
    search_fields = ("first_name", "last_name", "username", "user__email", "phone", "bio")
    ordering = ("first_name", "last_name")
    readonly_fields = ("id", "photo_preview")
    autocomplete_fields = ("user",)
    date_hierarchy = "birth_date"
    list_per_page = 25
    list_select_related = ("user",)
    actions = ["reset_photo_to_default", "export_as_csv"]

    fieldsets = (
        (_("Conta"), {"fields": ("id", "user")}),
        (_("Dados pessoais"), {
            "fields": (("first_name", "last_name"), "username", ("gender", "birth_date")),
        }),
        (_("Contato"), {"fields": ("phone", "instagram")}),
        (_("Sobre"), {"fields": ("bio",)}),
        (_("Foto"), {"fields": ("photo", "photo_preview")}),
    )

    # ── Colunas customizadas ──────────────────────────────────────────────

    @admin.display(description="")
    def avatar(self, obj):
        return thumbnail(obj.photo_url)

    @admin.display(description=_("Nome completo"), ordering="first_name")
    def full_name(self, obj):
        return obj.get_full_name()

    @admin.display(description=_("E-mail"), ordering="user__email")
    def user_email(self, obj):
        return obj.user.email

    @admin.display(description=_("Gênero"))
    def gender_display(self, obj):
        return gender_badge(obj.gender)

    @admin.display(description=_("Conta ativa?"), boolean=True, ordering="user__is_active")
    def is_user_active(self, obj):
        return obj.user.is_active

    @admin.display(description=_("Pré-visualização"))
    def photo_preview(self, obj):
        return thumbnail(obj.photo_url, size=120)

    # ── Actions ────────────────────────────────────────────────────────────

    @admin.action(description="🖼️ Restaurar foto padrão")
    def reset_photo_to_default(self, request, queryset):
        updated = 0
        for employee in queryset:
            employee.photo = None
            employee.save()
            updated += 1
        self.message_user(request, f"{updated} funcionário(s) com a foto restaurada para o padrão.")