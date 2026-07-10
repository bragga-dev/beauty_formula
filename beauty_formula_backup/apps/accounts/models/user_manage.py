from django.contrib.auth.models import BaseUserManager
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from .constants import ROLE_ADMIN, ROLE_CLIENT


class UserManager(BaseUserManager):

    def _create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError(_('O e-mail é obrigatório.'))

        email = self.normalize_email(email)
        role  = extra_fields.get('role', ROLE_CLIENT)

        # ─────────────────────────────────────────────
        # ADMIN ROOT
        # ─────────────────────────────────────────────
        if role == ROLE_ADMIN:
            extra_fields.setdefault('is_staff', True)
            extra_fields.setdefault('is_superuser', True)
            extra_fields.setdefault('is_active', True)
            extra_fields.setdefault('is_trusty', True)

        # ─────────────────────────────────────────────
        # MEMBER e CHURCH — precisam confirmação/aprovação
        # ─────────────────────────────────────────────
        else:
            extra_fields.setdefault('is_staff', False)
            extra_fields.setdefault('is_superuser', False)
            extra_fields.setdefault('is_active', False)
            extra_fields.setdefault('is_trusty', False)

        user = self.model(
            email=email,
            last_login=timezone.now(),
            date_joined=timezone.now(),
            **extra_fields,
        )
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        """
        Cria CLIENT ou EMPLOYEE.
        ADMIN só pode ser criado via create_superuser.
        """
        role = extra_fields.get('role', ROLE_CLIENT)

        if role == ROLE_ADMIN:
            raise ValueError(_('Use create_superuser para criar administradores.'))

        extra_fields.setdefault('role', ROLE_CLIENT)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password=None, **extra_fields):
        """
        Cria ADMIN ROOT.
        Chamado por: python manage.py createsuperuser
        """
        extra_fields.setdefault('role', ROLE_ADMIN)
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        extra_fields.setdefault('is_trusty', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError(_('Superuser deve ter is_staff=True.'))
        if extra_fields.get('is_superuser') is not True:
            raise ValueError(_('Superuser deve ter is_superuser=True.'))

        return self._create_user(email, password, **extra_fields)