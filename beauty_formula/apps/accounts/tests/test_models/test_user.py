import pytest
from django.db import IntegrityError
from django.contrib.auth import get_user_model
from beauty_formula.apps.accounts.models.constants import ROLE_ADMIN, ROLE_CLIENT, ROLE_EMPLOYEE

User = get_user_model()

pytestmark = pytest.mark.django_db


class TestUserModel:
    def test_create_user_client(self):
        """Testa criação de usuário com role CLIENT"""
        user = User.objects.create_user(
            email="client@example.com",
            password="pass123",
            role=ROLE_CLIENT
        )
        
        assert user.email == "client@example.com"
        assert user.role == ROLE_CLIENT
        assert user.is_client is True
        assert user.is_employee is False
        assert user.is_staff is False
        assert user.is_superuser is False
        assert user.is_active is False
        assert user.is_trusty is False
        assert user.check_password("pass123") is True

    def test_create_user_employee(self):
        """Testa criação de usuário com role EMPLOYEE"""
        user = User.objects.create_user(
            email="employee@example.com",
            password="pass123",
            role=ROLE_EMPLOYEE
        )
        
        assert user.email == "employee@example.com"
        assert user.role == ROLE_EMPLOYEE
        assert user.is_client is False
        assert user.is_employee is True
        assert user.is_staff is False
        assert user.is_superuser is False
        assert user.is_active is False
        assert user.is_trusty is False

    def test_create_superuser(self):
        """Testa criação de superuser (ADMIN)"""
        admin = User.objects.create_superuser(
            email="admin@example.com",
            password="admin123"
        )
        
        assert admin.email == "admin@example.com"
        assert admin.role == ROLE_ADMIN
        assert admin.is_staff is True
        assert admin.is_superuser is True
        assert admin.is_active is True
        assert admin.is_trusty is True
        assert admin.check_password("admin123") is True

    def test_create_user_without_email_raises_error(self):
        """Testa que criar usuário sem email levanta erro"""
        with pytest.raises(ValueError) as exc_info:
            User.objects.create_user(email="", password="pass123")
        assert "O e-mail é obrigatório" in str(exc_info.value)

    def test_create_user_with_role_admin_raises_error(self):
        """Testa que criar usuário com role ADMIN usando create_user levanta erro"""
        with pytest.raises(ValueError) as exc_info:
            User.objects.create_user(
                email="admin@example.com",
                password="pass123",
                role=ROLE_ADMIN
            )
        assert "Use create_superuser para criar administradores" in str(exc_info.value)

    def test_create_superuser_without_staff_raises_error(self):
        """Testa que criar superuser sem is_staff levanta erro"""
        with pytest.raises(ValueError) as exc_info:
            User.objects.create_superuser(
                email="admin@example.com",
                password="admin123",
                is_staff=False
            )
        assert "Superuser deve ter is_staff=True" in str(exc_info.value)

    def test_create_superuser_without_superuser_raises_error(self):
        """Testa que criar superuser sem is_superuser levanta erro"""
        with pytest.raises(ValueError) as exc_info:
            User.objects.create_superuser(
                email="admin@example.com",
                password="admin123",
                is_superuser=False
            )
        assert "Superuser deve ter is_superuser=True" in str(exc_info.value)

    def test_user_str_method(self):
        """Testa o método __str__ do User"""
        user = User.objects.create_user(
            email="test@example.com",
            password="pass123"
        )
        assert str(user) == "test@example.com"

    def test_user_is_client_property(self):
        """Testa a property is_client"""
        client_user = User.objects.create_user(
            email="client@example.com",
            password="pass123",
            role=ROLE_CLIENT
        )
        assert client_user.is_client is True
        assert client_user.is_employee is False

    def test_user_is_employee_property(self):
        """Testa a property is_employee"""
        employee_user = User.objects.create_user(
            email="employee@example.com",
            password="pass123",
            role=ROLE_EMPLOYEE
        )
        assert employee_user.is_employee is True
        assert employee_user.is_client is False

    def test_user_email_unique_constraint(self):
        """Testa que email deve ser único"""
        User.objects.create_user(
            email="unique@example.com",
            password="pass123"
        )
        
        with pytest.raises(IntegrityError):
            User.objects.create_user(
                email="unique@example.com",
                password="pass456"
            )
    def test_user_email_normalization(self):
        """Testa normalização de email - Django normaliza apenas o domínio"""
        user = User.objects.create_user(
            email="TEST@EXAMPLE.COM",
            password="pass123"
        )
        # Django normaliza apenas o domínio para lowercase
        # A parte local 'TEST' permanece maiúscula
        assert user.email == "TEST@example.com"
        
    def test_user_meta_options(self):
        """Testa as opções Meta do User"""
        assert User._meta.verbose_name == "Usuário"
        assert User._meta.verbose_name_plural == "Usuários"