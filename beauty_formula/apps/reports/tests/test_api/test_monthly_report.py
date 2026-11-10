"""Balanço mensal: só admin ou gerente."""
from datetime import timedelta

import pytest
from django.utils import timezone

from beauty_formula.apps.services.models.scheduling import Scheduling

pytestmark = pytest.mark.django_db

BASE = "/reports/monthly-balance"


@pytest.fixture
def completed(make_scheduling):
    return make_scheduling(status=Scheduling.SchedulingStatus.COMPLETED, days_ahead=-1, completed_at=timezone.now() - timedelta(hours=20))


def _ym():
    d = timezone.localdate()
    return {"year": d.year, "month": d.month}


@pytest.mark.parametrize("who", ["root_admin", "manager_user"])
def test_balance_for_admin_and_manager(api, request, completed, who):
    r = api.get(BASE, user=request.getfixturevalue(who), **_ym())
    assert r.status_code == 200, r.content
    assert r.json()


def test_balance_defaults_to_current_month(api, root_admin):
    assert api.get(BASE, user=root_admin).status_code == 200


@pytest.mark.parametrize("month", [13, 99])
def test_balance_rejects_invalid_month(api, root_admin, month):
    assert api.get(BASE, user=root_admin, year=2026, month=month).status_code == 400


def test_balance_for_explicit_month(api, root_admin, completed):
    r = api.get(BASE, user=root_admin, **_ym())
    assert r.status_code == 200 and r.json()["year"] == _ym()["year"]


def test_history(api, manager_user, completed):
    assert api.get(f"{BASE}/history", user=manager_user).status_code == 200


def test_pdf(api, root_admin, completed):
    r = api.get(f"{BASE}/pdf", user=root_admin, **_ym())
    assert r.status_code == 200, r.content[:200]
    assert r["Content-Type"] == "application/pdf" and r.content.startswith(b"%PDF")


@pytest.mark.parametrize("who", ["verified_client", "verified_employee"])
def test_forbidden_for_client_and_employee(api, request, who):
    user = request.getfixturevalue(who)
    for path in (BASE, f"{BASE}/history", f"{BASE}/pdf"):
        assert api.get(path, user=user).status_code == 403


def test_requires_authentication(api):
    assert api.get(BASE).status_code == 401