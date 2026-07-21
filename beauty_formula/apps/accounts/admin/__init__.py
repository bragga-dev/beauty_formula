"""
Pacote admin do app accounts.

Dividido em um arquivo por model (user_admin, client_admin, employee_admin)
+ mixins.py (badges/ícones/export CSV compartilhados) + forms.py (forms do User).

Os imports abaixo são necessários para que o autodiscover do Django
(`django.contrib.admin.autodiscover`) registre os ModelAdmins — sem eles,
o Python nunca executaria o código de `@admin.register(...)` de cada módulo.
"""
from beauty_formula.apps.accounts.admin.client_admin import ClientInline, ClientAdmin, AgeRangeFilter
from beauty_formula.apps.accounts.admin.employee_admin import EmployeeAdmin, EmployeeInline, HasBioFilter
from beauty_formula.apps.accounts.admin.user_admin import UserAdmin
from beauty_formula.apps.accounts.admin.forms import UserChangeForm, UserCreationForm


__all__ = [
    "UserAdmin",
    "ClientAdmin",
    "ClientInline",
    "AgeRangeFilter",
    "EmployeeAdmin",
    "EmployeeInline",
    "HasBioFilter",
    "UserChangeForm",
    "UserCreationForm",
]