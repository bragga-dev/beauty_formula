"""
Forms usados pelo UserAdmin.
Precisam existir porque o User customizado usa `email` como USERNAME_FIELD
e não possui campo `username` — os forms padrão do Django (UserCreationForm/
UserChangeForm) esperam `username` e quebrariam sem esse ajuste.
"""
from django.contrib.auth.forms import (
    UserChangeForm as BaseUserChangeForm,
    UserCreationForm as BaseUserCreationForm,
)

from beauty_formula.apps.accounts.models import User


class UserCreationForm(BaseUserCreationForm):
    class Meta(BaseUserCreationForm.Meta):
        model = User
        fields = ("email",)


class UserChangeForm(BaseUserChangeForm):
    class Meta(BaseUserChangeForm.Meta):
        model = User
        fields = "__all__"