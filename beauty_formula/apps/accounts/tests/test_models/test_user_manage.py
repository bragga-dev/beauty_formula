import pytest
from django.contrib.auth import get_user_model
from beauty_formula.apps.accounts.models import ROLE_ADMIN, ROLE_CLIENT, ROLE_EMPLOYEE


pytestmark = pytest.mark.django_db


class TestUserManager:
    def test_user_manager_create_user_default_role(self):
        """Testa criação de usuário com role padrão (CLIENT)"""
        user = get_user_model().objects.create_user(
            email="default@example.com",
            password="pass123"
        )
        assert user.role == ROLE_CLIENT

    def test_user_manager_create_user_with_custom_role(self):
        """Testa criação de usuário com role customizada"""
        user = get_user_model().objects.create_user(
            email="employee@example.com",
            password="pass123",
            role=ROLE_EMPLOYEE
        )
        assert user.role == ROLE_EMPLOYEE

    def test_user_manager_create_superuser_auto_sets_permissions(self):
        """Testa que create_superuser define automaticamente permissões"""
        admin = get_user_model().objects.create_superuser(
            email="superadmin@example.com",
            password="admin123"
        )
        assert admin.is_staff is True
        assert admin.is_superuser is True
        assert admin.is_active is True
        assert admin.is_trusty is True

    def test_user_manager_create_user_inactive_by_default(self):
        """Testa que usuários normais são criados inativos"""
        user = get_user_model().objects.create_user(
            email="user@example.com",
            password="pass123"
        )
        assert user.is_active is False
        assert user.is_staff is False
        assert user.is_superuser is False
        assert user.is_trusty is False