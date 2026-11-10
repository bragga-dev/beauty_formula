"""Quem pode (des)ativar quem, gerentes e criação de funcionário."""
import pytest

from beauty_formula.apps.accounts.models import User
from beauty_formula.apps.accounts.repositories.user_repository import activate_user

pytestmark = pytest.mark.django_db


def test_manager_cannot_deactivate_admin(api, manager_user, root_admin):
    assert api.post(f"/auth/deactive-user/{root_admin.id}", user=manager_user).status_code == 403
    root_admin.refresh_from_db()
    assert root_admin.is_active


def test_manager_cannot_deactivate_other_manager(api, manager_user):
    other = User.objects.create_user(email="g2@example.com", password="Senha12345!", role="manager")
    assert api.post(f"/auth/deactive-user/{other.id}", user=manager_user).status_code == 403


def test_nobody_deactivates_self_here(api, manager_user):
    assert api.post(f"/auth/deactive-user/{manager_user.id}", user=manager_user).status_code == 403


def test_manager_can_deactivate_and_reactivate_client(api, manager_user, verified_client):
    assert api.post(f"/auth/deactive-user/{verified_client.id}", user=manager_user).status_code == 201
    verified_client.refresh_from_db()
    assert verified_client.is_active is False
    assert api.post(f"/auth/reactivate-user/{verified_client.id}", user=manager_user).status_code == 201
    verified_client.refresh_from_db()
    assert verified_client.is_active and verified_client.is_trusty


def test_deactivation_revokes_sessions(api, verified_client, root_admin):
    from beauty_formula.apps.core.tokens.cookies import REFRESH_COOKIE_NAME
    r = api.post("/auth/login", {"email": verified_client.email, "password": "Senha12345!"})
    cookie = r.cookies[REFRESH_COOKIE_NAME].value
    api.post(f"/auth/deactive-user/{verified_client.id}", user=root_admin)
    api._c.cookies[REFRESH_COOKIE_NAME] = cookie
    assert api.post("/auth/refresh").status_code == 401


def test_activate_user_sets_trusty_even_if_already_active(db):
    u = User.objects.create_user(email="a@example.com", password="Senha12345!", role="client")
    u.is_active, u.is_trusty = True, False
    u.save()
    assert activate_user(u).is_trusty is True


def test_register_employee_returns_no_tokens_and_creates_inactive_free_profile(api, manager_user):
    r = api.post("/auth/register-employee", {"email": "novo.func@example.com"}, user=manager_user)
    assert r.status_code in (200, 201)
    assert "access" not in r.json() and "refresh" not in r.json()
    assert User.objects.get(email="novo.func@example.com").role == "employee"


def test_register_employee_forbidden_for_client(api, verified_client):
    assert api.post("/auth/register-employee", {"email": "x@example.com"}, user=verified_client).status_code == 403


def test_admin_creates_manager_and_manager_is_listed(api, root_admin):
    r = api.post("/managers/", {"email": "g3@example.com", "first_name": "G", "last_name": "Três"}, user=root_admin)
    assert r.status_code == 201
    assert api.get("/managers/", user=root_admin).status_code == 200
    assert User.objects.get(email="g3@example.com").role == "manager"


def test_create_manager_duplicate_email_is_409(api, root_admin, manager_user):
    r = api.post("/managers/", {"email": manager_user.email, "first_name": "G", "last_name": "X"}, user=root_admin)
    assert r.status_code == 409