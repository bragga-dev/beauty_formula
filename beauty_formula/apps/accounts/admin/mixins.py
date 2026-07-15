"""
Mixins e helpers visuais compartilhados entre os ModelAdmins do app accounts.
Mantém badges coloridos, ícones e a action de exportação em um único lugar
para não duplicar HTML/CSS entre UserAdmin, ClientAdmin e EmployeeAdmin.
"""
import csv

from django.http import HttpResponse
from django.utils.html import format_html

from beauty_formula.apps.core.constants.gender import Gender


# ── Cores por tipo de conta ───────────────────────────────────────────────────

ROLE_STYLE = {
    "admin":    {"label": "Admin",       "icon": "👑", "bg": "#7c3aed", "fg": "#fff"},
    "employee": {"label": "Funcionário", "icon": "🛠️", "bg": "#0ea5e9", "fg": "#fff"},
    "client":   {"label": "Cliente",     "icon": "🧑", "bg": "#16a34a", "fg": "#fff"},
}

GENDER_STYLE = {
    Gender.MALE:   {"label": "Masculino",           "icon": "♂",  "bg": "#3b82f6"},
    Gender.FEMALE: {"label": "Feminino",             "icon": "♀",  "bg": "#ec4899"},
    Gender.OTHER:  {"label": "Prefiro não informar", "icon": "⚧",  "bg": "#6b7280"},
}


def _pill(label, icon, bg, fg="#fff"):
    return format_html(
        '<span style="display:inline-block;padding:2px 10px;border-radius:999px;'
        'font-size:11px;font-weight:600;letter-spacing:.02em;background:{};color:{};'
        'white-space:nowrap;">{} {}</span>',
        bg, fg, icon, label,
    )


def role_badge(role: str):
    """Badge colorido para o campo `role` do User (admin/employee/client)."""
    style = ROLE_STYLE.get(role, {"label": role, "icon": "❔", "bg": "#6b7280", "fg": "#fff"})
    return _pill(style["label"], style["icon"], style["bg"], style["fg"])


def gender_badge(gender: str):
    """Badge colorido para o campo `gender` de Client/Employee."""
    style = GENDER_STYLE.get(gender, {"label": gender or "—", "icon": "•", "bg": "#6b7280"})
    return _pill(style["label"], style["icon"], style["bg"])


def bool_icon(value: bool, true_label="Sim", false_label="Não"):
    """✅ / ❌ coloridos para campos booleanos (is_active, is_staff, is_trusty...)."""
    if value:
        return format_html('<span style="color:#16a34a;font-weight:700;">✅ {}</span>', true_label)
    return format_html('<span style="color:#dc2626;font-weight:700;">❌ {}</span>', false_label)


def thumbnail(url: str, size=40):
    if not url:
        return "—"
    return format_html(
        '<img src="{}" style="width:{}px;height:{}px;border-radius:50%;'
        'object-fit:cover;border:1px solid #e5e7eb;" />',
        url, size, size,
    )


class ExportCsvMixin:
    """
    Action genérica de exportação para CSV.
    Cada ModelAdmin que a usa define `csv_export_fields = (...)`
    com o nome dos campos (ou properties) do model a exportar.
    """
    csv_export_fields: tuple = ()

    @staticmethod
    def _field_label(model, field_name):
        try:
            return model._meta.get_field(field_name).verbose_name
        except Exception:
            return field_name

    def export_as_csv(self, request, queryset):
        model = queryset.model
        fields = self.csv_export_fields or [f.name for f in model._meta.fields]

        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = f"attachment; filename={model._meta.verbose_name_plural}.csv"

        writer = csv.writer(response)
        writer.writerow([self._field_label(model, f) for f in fields])

        for obj in queryset:
            writer.writerow([getattr(obj, f, "") for f in fields])

        return response

    export_as_csv.short_description = "⬇️ Exportar selecionados para CSV"