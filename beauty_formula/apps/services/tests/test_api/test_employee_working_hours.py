"""Expediente do funcionário: só o próprio funcionário gerencia."""
import uuid
from datetime import time

import pytest

from beauty_formula.apps.services.models.employee_works_hours import EmployeeWorkingHours

pytestmark = pytest.mark.django_db

BASE = "/employee-working-hours/"


@pytest.fixture
def monday_hours(employee):
    return EmployeeWorkingHours.objects.create(employee=employee, weekday=0, start_time=time(8, 0), end_time=time(12, 0))


def test_create_working_hours(api, verified_employee, employee):
    r = api.post(BASE, {"weekday": 1, "start_time": "09:00", "end_time": "17:00"}, user=verified_employee)
    assert r.status_code == 201, r.content
    wh = EmployeeWorkingHours.objects.get(employee=employee)
    assert wh.weekday == 1 and wh.start_time == time(9, 0)


def test_create_rejects_start_after_end(api, verified_employee):
    r = api.post(BASE, {"weekday": 1, "start_time": "18:00", "end_time": "09:00"}, user=verified_employee)
    assert r.status_code == 400
    assert not EmployeeWorkingHours.objects.exists()


def test_create_rejects_overlap(api, verified_employee, monday_hours):
    r = api.post(BASE, {"weekday": 0, "start_time": "10:00", "end_time": "14:00"}, user=verified_employee)
    assert r.status_code == 400


def test_create_rejects_invalid_weekday(api, verified_employee):
    assert api.post(BASE, {"weekday": 9, "start_time": "09:00", "end_time": "10:00"}, user=verified_employee).status_code == 422


def test_list_my_working_hours(api, verified_employee, monday_hours):
    r = api.get(f"{BASE}list-my-working-hours", user=verified_employee)
    assert r.status_code == 200 and len(r.json()) == 1


def test_list_does_not_leak_other_employees(api, other_verified_employee, monday_hours):
    assert api.get(f"{BASE}list-my-working-hours", user=other_verified_employee).json() == []


def test_update_working_hours(api, verified_employee, monday_hours):
    r = api.patch(f"{BASE}{monday_hours.id}", {"end_time": "13:00"}, user=verified_employee)
    assert r.status_code == 200, r.content
    monday_hours.refresh_from_db()
    assert monday_hours.end_time == time(13, 0) and monday_hours.start_time == time(8, 0)


def test_update_rejects_invalid_range(api, verified_employee, monday_hours):
    assert api.patch(f"{BASE}{monday_hours.id}", {"end_time": "07:00"}, user=verified_employee).status_code == 400


def test_update_unknown_is_404(api, verified_employee):
    assert api.patch(f"{BASE}{uuid.uuid4()}", {"end_time": "13:00"}, user=verified_employee).status_code == 404


def test_cannot_update_or_delete_other_employees_hours(api, other_verified_employee, monday_hours):
    assert api.patch(f"{BASE}{monday_hours.id}", {"end_time": "13:00"}, user=other_verified_employee).status_code == 404
    assert api.delete(f"{BASE}{monday_hours.id}", user=other_verified_employee).status_code == 404
    assert EmployeeWorkingHours.objects.filter(id=monday_hours.id).exists()


def test_delete_working_hours(api, verified_employee, monday_hours):
    assert api.delete(f"{BASE}{monday_hours.id}", user=verified_employee).status_code in (200, 204)
    assert not EmployeeWorkingHours.objects.filter(id=monday_hours.id).exists()


@pytest.mark.parametrize("who", ["verified_client", "manager_user", "root_admin"])
def test_only_employees_manage_working_hours(api, request, who):
    assert api.get(f"{BASE}list-my-working-hours", user=request.getfixturevalue(who)).status_code in (403, 404)
    assert api.post(BASE, {"weekday": 1, "start_time": "09:00", "end_time": "17:00"}, user=request.getfixturevalue(who)).status_code in (403, 404)