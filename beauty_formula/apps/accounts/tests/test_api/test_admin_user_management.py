"""Gestão de usuários por admin/gerente: cadastro de funcionário, promoção, (des)ativação e consulta."""
import uuid

import pytest

from beauty_formula.apps.accounts.models import User
from beauty_formula.apps.accounts.models.client import Client
from beauty_formula.apps.accounts.models.employee import Employee
from beauty_formula.apps.services.models.scheduling import Scheduling

pytestmark = pytest.mark.django_db


# ── Cadastro de funcionário ─────────────────────────────────────────────────

@pytest.mark.parametrize("who", ["root_admin", "manager_user"])
def test_register_employee(api, request, who, celery_delay):
    r = api.post("/auth/register-employee", {"email": "novo.func@example.com"}, user=request.getfixturevalue(who))
    assert r.status_code == 201, r.content
    user = User.objects.get(email="novo.func@example.com")
    assert user.role == "employee" and Employee.objects.filter(user=user).exists()


def test_register_employee_duplicate_is_409(api, root_admin, verified_employee):
    assert api.post("/auth/register-employee", {"email": verified_employee.email}, user=root_admin).status_code == 409


@pytest.mark.parametrize("who", ["verified_client", "verified_employee"])
def test_register_employee_forbidden(api, request, who):
    assert api.post("/auth/register-employee", {"email": "x@example.com"}, user=request.getfixturevalue(who)).status_code == 403
    assert not User.objects.filter(email="x@example.com").exists()


# ── Promoção cliente → funcionário ──────────────────────────────────────────

def test_promote_client_to_employee(api, root_admin, verified_client, client_profile):
    r = api.post(f"/auth/promote-client-to-employee/{verified_client.id}", user=root_admin)
    assert r.status_code == 201, r.content
    verified_client.refresh_from_db()
    assert verified_client.role == "employee"
    assert Employee.objects.filter(user=verified_client).exists()
    assert not Client.objects.filter(user=verified_client).exists()


def test_promote_blocked_by_active_scheduling(api, root_admin, verified_client, make_scheduling):
    make_scheduling(status=Scheduling.SchedulingStatus.CONFIRMED, days_ahead=3)
    r = api.post(f"/auth/promote-client-to-employee/{verified_client.id}", user=root_admin)
    assert r.status_code == 409
    verified_client.refresh_from_db()
    assert verified_client.role == "client"


def test_promote_unknown_is_404(api, root_admin):
    assert api.post(f"/auth/promote-client-to-employee/{uuid.uuid4()}", user=root_admin).status_code == 404


def test_promote_forbidden_for_employee(api, verified_employee, verified_client):
    assert api.post(f"/auth/promote-client-to-employee/{verified_client.id}", user=verified_employee).status_code == 403


# ── Ativar / desativar ──────────────────────────────────────────────────────

@pytest.mark.parametrize("who", ["root_admin", "manager_user"])
def test_deactivate_and_reactivate(api, request, verified_client, who):
    user = request.getfixturevalue(who)
    assert api.post(f"/auth/deactive-user/{verified_client.id}", user=user).status_code == 201
    verified_client.refresh_from_db()
    assert verified_client.is_active is False
    assert api.post(f"/auth/reactivate-user/{verified_client.id}", user=user).status_code == 201
    verified_client.refresh_from_db()
    assert verified_client.is_active is True


def test_deactivated_user_cannot_authenticate(api, root_admin, verified_client):
    api.post(f"/auth/deactive-user/{verified_client.id}", user=root_admin)
    assert api.get("/auth/me", user=verified_client).status_code in (401, 403)


def test_deactivate_unknown_is_404(api, root_admin):
    assert api.post(f"/auth/deactive-user/{uuid.uuid4()}", user=root_admin).status_code == 404
    assert api.post(f"/auth/reactivate-user/{uuid.uuid4()}", user=root_admin).status_code == 404


def test_deactivate_forbidden_for_client(api, verified_client, other_verified_client):
    assert api.post(f"/auth/deactive-user/{other_verified_client.id}", user=verified_client).status_code == 403


# ── Consulta ────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("who", ["root_admin", "manager_user"])
def test_list_users(api, request, verified_client, verified_employee, who):
    r = api.get("/admin/list-users", user=request.getfixturevalue(who))
    assert r.status_code == 200 and r.json()["total"] >= 3


def test_list_users_filters(api, root_admin, verified_client, verified_employee):
    assert api.get("/admin/list-users", user=root_admin, role="employee").json()["total"] == 1
    assert api.get("/admin/list-users", user=root_admin, search=verified_client.email).json()["total"] == 1
    verified_client.is_active = False
    verified_client.save(update_fields=["is_active"])
    assert api.get("/admin/list-users", user=root_admin, is_active="false").json()["total"] == 1


def test_detail_user(api, manager_user, verified_client):
    r = api.get(f"/admin/detail-user/{verified_client.id}", user=manager_user)
    assert r.status_code == 200 and r.json()["email"] == verified_client.email
    assert api.get(f"/admin/detail-user/{uuid.uuid4()}", user=manager_user).status_code == 404


@pytest.mark.parametrize("who", ["verified_client", "verified_employee"])
def test_admin_queries_forbidden(api, request, verified_client, who):
    user = request.getfixturevalue(who)
    assert api.get("/admin/list-users", user=user).status_code == 403
    assert api.get(f"/admin/detail-user/{verified_client.id}", user=user).status_code == 403