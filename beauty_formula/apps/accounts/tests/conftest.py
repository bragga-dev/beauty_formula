import pytest
from beauty_formula.apps.accounts.models import User


@pytest.fixture
def client_user():
    """Cria um usuário com role CLIENT para testes"""
    return User.objects.create_user(
        email="test@example.com",
        password="password123",
        role="client"
    )


@pytest.fixture
def employee_user():
    """Cria um usuário com role EMPLOYEE para testes"""
    return User.objects.create_user(
        email="employee@example.com",
        password="password123",
        role="employee"
    )


@pytest.fixture
def admin_user():
    """Cria um usuário admin para testes"""
    return User.objects.create_superuser(
        email="admin@example.com",
        password="admin123"
    )