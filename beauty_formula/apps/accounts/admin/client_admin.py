from datetime import date

from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from beauty_formula.apps.accounts.admin.mixins import (
    ExportCsvMixin,
    gender_badge,
    thumbnail,
)
from beauty_formula.apps.accounts.models import Client


# ── Inline (usado dentro do UserAdmin) ────────────────────────────────────────

class ClientInline(admin.StackedInline):
    model = Client
    extra = 0
    max_num = 1
    can_delete = False
    verbose_name = _("Perfil de Cliente")
    verbose_name_plural = _("Perfil de Cliente")
    fk_name = "user"
    fields = (
        ("first_name", "last_name", "username"),
        ("phone", "gender", "birth_date"),
        "instagram",
        "photo",
    )


# ── Filtro customizado: faixa etária ──────────────────────────────────────────

class AgeRangeFilter(admin.SimpleListFilter):
    title = _("faixa etária")
    parameter_name = "faixa_etaria"

    def lookups(self, request, model_admin):
        return (
            ("0-17", "Menor de idade"),
            ("18-29", "18 a 29 anos"),
            ("30-49", "30 a 49 anos"),
            ("50+", "50+ anos"),
        )

    def queryset(self, request, queryset):
        from datetime import timedelta

        today = date.today()
        value = self.value()
        if not value:
            return queryset

        def years_ago(years):
            return today - timedelta(days=int(years * 365.25))

        if value == "0-17":
            return queryset.filter(birth_date__gt=years_ago(18))
        if value == "18-29":
            return queryset.filter(birth_date__lte=years_ago(18), birth_date__gt=years_ago(30))
        if value == "30-49":
            return queryset.filter(birth_date__lte=years_ago(30), birth_date__gt=years_ago(50))
        if value == "50+":
            return queryset.filter(birth_date__lte=years_ago(50))
        return queryset


# ── ModelAdmin ─────────────────────────────────────────────────────────────────

@admin.register(Client)
class ClientAdmin(ExportCsvMixin, admin.ModelAdmin):
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
    list_filter = ("gender", AgeRangeFilter, "user__is_active")
    search_fields = ("first_name", "last_name", "username", "user__email", "phone")
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
        for client in queryset:
            client.photo = None
            client.save()
            updated += 1
        self.message_user(request, f"{updated} cliente(s) com a foto restaurada para o padrão.")