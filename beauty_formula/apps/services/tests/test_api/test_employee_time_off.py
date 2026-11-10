"""Bloqueios de agenda (recorrentes e pontuais) do funcionário."""
import uuid
from datetime import time, timedelta

import pytest
from django.utils import timezone

from beauty_formula.apps.services.models.employee_time_off import EmployeeTimeOff

pytestmark = pytest.mark.django_db

BASE = "/employee-time-off/"


def _punctual_payload(start_in_hours=48, hours=2, block_type="medical"):
    start = timezone.now() + timedelta(hours=start_in_hours)
    return {"block_type": block_type, "start_datetime": start.isoformat(), "end_datetime": (start + timedelta(hours=hours)).isoformat()}


RECURRING = {"block_type": "lunch", "weekday": 1, "start_time": "12:00", "end_time": "13:00"}


@pytest.fixture
def recurring(api, verified_employee):
    r = api.post(f"{BASE}recurring/", RECURRING, user=verified_employee)
    assert r.status_code == 201, r.content
    return r.json()


@pytest.fixture
def punctual(api, verified_employee):
    r = api.post(f"{BASE}punctual/", _punctual_payload(), user=verified_employee)
    assert r.status_code == 201, r.content
    return r.json()


# ── Criação ─────────────────────────────────────────────────────────────────

def test_create_recurring(api, verified_employee, employee):
    r = api.post(f"{BASE}recurring/", RECURRING, user=verified_employee)
    assert r.status_code == 201
    t = EmployeeTimeOff.objects.get(employee=employee)
    assert t.is_recurring and t.weekday == 1 and t.start_time == time(12, 0)


def test_create_recurring_rejects_inverted_times(api, verified_employee):
    r = api.post(f"{BASE}recurring/", {**RECURRING, "start_time": "14:00", "end_time": "13:00"}, user=verified_employee)
    assert r.status_code in (400, 422)


def test_create_punctual(api, verified_employee, employee):
    assert api.post(f"{BASE}punctual/", _punctual_payload(), user=verified_employee).status_code == 201
    assert EmployeeTimeOff.objects.get(employee=employee).is_punctual


def test_create_punctual_rejects_end_before_start(api, verified_employee):
    p = _punctual_payload()
    p["end_datetime"] = (timezone.now() + timedelta(hours=1)).isoformat()
    assert api.post(f"{BASE}punctual/", p, user=verified_employee).status_code in (400, 422)


def test_create_punctual_conflict_is_409(api, verified_employee, punctual):
    r = api.post(f"{BASE}punctual/", _punctual_payload(), user=verified_employee)
    assert r.status_code in (400, 409)
    assert EmployeeTimeOff.objects.count() == 1


def test_invalid_block_type_is_422(api, verified_employee):
    assert api.post(f"{BASE}punctual/", _punctual_payload(block_type="xyz"), user=verified_employee).status_code == 422


# ── Listagens ───────────────────────────────────────────────────────────────

@pytest.mark.parametrize("route, expected", [
    ("list-my-time-off", 2),
    ("list-my-recurring-time-off", 1),
    ("list-my-punctual-time-off", 1),
    ("list-my-upcoming-time-off", 2),
])
def test_listings(api, verified_employee, recurring, punctual, route, expected):
    r = api.get(f"{BASE}{route}", user=verified_employee)
    assert r.status_code == 200, r.content
    body = r.json()
    items = body["items"] if isinstance(body, dict) else body
    assert len(items) == expected


def test_list_by_block_type(api, verified_employee, recurring, punctual):
    r = api.get(f"{BASE}list-my-time-off-by-block-type/lunch", user=verified_employee)
    assert r.status_code == 200
    body = r.json()
    assert len(body["items"] if isinstance(body, dict) else body) == 1


def test_list_on_date(api, verified_employee, punctual):
    day = (timezone.now() + timedelta(hours=48)).date().isoformat()
    r = api.get(f"{BASE}list-my-time-off-on-date", user=verified_employee, target_date=day)
    assert r.status_code == 200
    body = r.json()
    assert len(body["items"] if isinstance(body, dict) else body) >= 1


def test_list_active_returns_only_blocks_in_effect_now(api, verified_employee, employee):
    now = timezone.now()
    EmployeeTimeOff.objects.create(
        employee=employee, block_type="medical", block_modality=EmployeeTimeOff.BlockModality.PUNCTUAL,
        start_datetime=now - timedelta(hours=1), end_datetime=now + timedelta(hours=1),
    )
    EmployeeTimeOff.objects.create(
        employee=employee, block_type="other", block_modality=EmployeeTimeOff.BlockModality.PUNCTUAL,
        start_datetime=now + timedelta(days=5), end_datetime=now + timedelta(days=5, hours=1),
    )
    body = api.get(f"{BASE}list-my-active-time-off", user=verified_employee).json()
    items = body["items"] if isinstance(body, dict) else body
    assert [i["block_type"] for i in items] == ["medical"]


def test_list_date_range(api, verified_employee, punctual):
    start = timezone.now().date().isoformat()
    end = (timezone.now() + timedelta(days=10)).date().isoformat()
    r = api.get(f"{BASE}list-my-time-off-date-range", user=verified_employee, start_date=start, end_date=end)
    assert r.status_code == 200


def test_listings_do_not_leak_between_employees(api, other_verified_employee, recurring, punctual):
    body = api.get(f"{BASE}list-my-time-off", user=other_verified_employee).json()
    assert len(body["items"] if isinstance(body, dict) else body) == 0


# ── Atualização ─────────────────────────────────────────────────────────────

def test_update_recurring(api, verified_employee, recurring):
    r = api.patch(f"{BASE}recurring/{recurring['id']}", {"end_time": "14:00"}, user=verified_employee)
    assert r.status_code == 200, r.content
    assert EmployeeTimeOff.objects.get(id=recurring["id"]).end_time == time(14, 0)


def test_update_punctual(api, verified_employee, punctual):
    r = api.patch(f"{BASE}punctual/{punctual['id']}", {"block_type": "personal"}, user=verified_employee)
    assert r.status_code == 200, r.content
    assert EmployeeTimeOff.objects.get(id=punctual["id"]).block_type == "personal"


def test_wrong_modality_update_is_rejected(api, verified_employee, recurring, punctual):
    assert api.patch(f"{BASE}punctual/{recurring['id']}", {"block_type": "personal"}, user=verified_employee).status_code in (400, 404)
    assert api.patch(f"{BASE}recurring/{punctual['id']}", {"block_type": "personal"}, user=verified_employee).status_code in (400, 404)


def test_update_unknown_is_404(api, verified_employee):
    assert api.patch(f"{BASE}recurring/{uuid.uuid4()}", {"end_time": "14:00"}, user=verified_employee).status_code == 404
    assert api.patch(f"{BASE}punctual/{uuid.uuid4()}", {"block_type": "other"}, user=verified_employee).status_code == 404


def test_cannot_update_other_employees_block(api, other_verified_employee, recurring):
    assert api.patch(f"{BASE}recurring/{recurring['id']}", {"end_time": "14:00"}, user=other_verified_employee).status_code in (403, 404)


# ── Exclusão ────────────────────────────────────────────────────────────────

def test_delete_one(api, verified_employee, recurring):
    assert api.delete(f"{BASE}{recurring['id']}", user=verified_employee).status_code in (200, 204)
    assert not EmployeeTimeOff.objects.filter(id=recurring["id"], is_active=True).exists()


def test_delete_unknown_is_404(api, verified_employee):
    assert api.delete(f"{BASE}{uuid.uuid4()}", user=verified_employee).status_code == 404


def test_cannot_delete_other_employees_block(api, other_verified_employee, recurring):
    assert api.delete(f"{BASE}{recurring['id']}", user=other_verified_employee).status_code in (403, 404)


def test_delete_recurring_punctual_by_type_and_all(api, verified_employee, recurring, punctual):
    assert api.delete(f"{BASE}delete-recurring", user=verified_employee).status_code in (200, 204)
    assert api.delete(f"{BASE}delete-punctual", user=verified_employee).status_code in (200, 204)
    body = api.get(f"{BASE}list-my-time-off", user=verified_employee).json()
    assert len(body["items"] if isinstance(body, dict) else body) == 0


def test_delete_by_block_type(api, verified_employee, recurring, punctual):
    assert api.delete(f"{BASE}delete-by-block-type/lunch", user=verified_employee).status_code in (200, 204)
    body = api.get(f"{BASE}list-my-time-off", user=verified_employee).json()
    assert len(body["items"] if isinstance(body, dict) else body) == 1


def test_delete_all(api, verified_employee, recurring, punctual):
    assert api.delete(f"{BASE}delete-all", user=verified_employee).status_code in (200, 204)
    body = api.get(f"{BASE}list-my-time-off", user=verified_employee).json()
    assert len(body["items"] if isinstance(body, dict) else body) == 0


@pytest.mark.parametrize("who", ["verified_client", "manager_user", "root_admin"])
def test_only_employees_manage_time_off(api, request, who):
    user = request.getfixturevalue(who)
    assert api.get(f"{BASE}list-my-time-off", user=user).status_code in (403, 404)
    assert api.post(f"{BASE}recurring/", RECURRING, user=user).status_code in (403, 404)