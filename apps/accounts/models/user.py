
import uuid
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from beauty_formula.apps.accounts.models.constants import ROLE_ADMIN, ROLE_CLIENT, ROLE_EMPLOYEE
from beauty_formula.apps.accounts.models.user_manage import UserManager



class User(AbstractBaseUser, PermissionsMixin):
    class UserRole(models.TextChoices):
        ADMIN  = ROLE_ADMIN,  "Administrador Root"
        CLIENT = ROLE_CLIENT, "Cliente"
        EMPLOYEE = ROLE_EMPLOYEE, "Funcionário"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    role = models.CharField(_("Tipo de usuário"), max_length=20, choices=UserRole.choices, default=UserRole.CLIENT,)

    email      = models.EmailField(_('E-mail'), max_length=255, unique=True)

    is_staff  = models.BooleanField(_('Staff'), default=False)
    is_active = models.BooleanField(_('Ativo?'), default=False)
    is_trusty = models.BooleanField(_('Confiável?'), default=False)

    date_joined = models.DateTimeField(_('Data de admissão'), default=timezone.now)
    created_at  = models.DateTimeField(_('Criado em'), auto_now_add=True)
    updated_at  = models.DateTimeField(_('Atualizado em'), auto_now=True)

    USERNAME_FIELD  = 'email'
    REQUIRED_FIELDS = []

    objects = UserManager()

    class Meta:
        verbose_name        = _('Usuário')
        verbose_name_plural = _('Usuários')

    # ── Helpers básicos ───────────────────────────────────────────────────────

    def email_user(self, subject, message, from_email=None):
        send_mail(subject, message, from_email, [self.email])

    def __str__(self):
        return self.email

    # ── Properties ───────────────────────────────────────────────────────────

    @property
    def is_client(self):
        return self.role == self.UserRole.CLIENT

    @property
    def is_employee(self):
        return self.role == self.UserRole.EMPLOYEE

   