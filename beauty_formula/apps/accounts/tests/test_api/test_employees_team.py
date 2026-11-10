"""Equipe: leitura pública; edição do funcionário pelo próprio, por admin ou por gerente."""
import uuid

import pytest

from beauty_formula.apps.conftest import image_file

pytestmark = pytest.mark.django_db

BASE = "/employees/team"


def test_public_team_list_and_filter_by_service(api, employee, service, employee_offers_service):
    assert api.get(BASE).json()["total"] >= 1
    assert api.get(BASE, service_id=str(service.id)).json()["total"] == 1
    assert api.get(BASE, service_id=str(uuid.uuid4())).json()["total"] == 0


def test_public_detail(api, employee):
    assert api.get(f"{BASE}/{employee.id}").status_code == 200
    assert api.get(f"{BASE}/{uuid.uuid4()}").status_code == 404


@pytest.mark.parametrize("who", ["root_admin", "manager_user"])
def test_admin_detail(api, request, employee, who):
    assert api.get(f"{BASE}/{employee.id}/admin", user=request.getfixturevalue(who)).status_code == 200


@pytest.mark.parametrize("who", ["verified_client", "verified_employee"])
def test_admin_detail_forbidden(api, request, employee, who):
    assert api.get(f"{BASE}/{employee.id}/admin", user=request.getfixturevalue(who)).status_code == 403


@pytest.mark.parametrize("who", ["root_admin", "manager_user"])
def test_booking_window_update(api, request, employee, who):
    r = api.patch(f"{BASE}/{employee.id}/booking-window", {"booking_window_days": 15}, user=request.getfixturevalue(who))
    assert r.status_code == 200, r.content
    employee.refresh_from_db()
    assert employee.booking_window_days == 15


@pytest.mark.parametrize("days", [0, -1, 100000])
def test_booking_window_rejects_invalid(api, root_admin, employee, days):
    assert api.patch(f"{BASE}/{employee.id}/booking-window", {"booking_window_days": days}, user=root_admin).status_code in (400, 422)


def test_booking_window_forbidden_for_employee_and_unknown(api, verified_employee, root_admin, employee):
    assert api.patch(f"{BASE}/{employee.id}/booking-window", {"booking_window_days": 10}, user=verified_employee).status_code == 403
    assert api.patch(f"{BASE}/{uuid.uuid4()}/booking-window", {"booking_window_days": 10}, user=root_admin).status_code == 404


@pytest.mark.parametrize("who", ["root_admin", "manager_user"])
def test_admin_edits_employee_profile(api, request, employee, who):
    r = api.patch(f"{BASE}/{employee.id}/profile", {"first_name": "Paula", "bio": "Especialista"}, user=request.getfixturevalue(who))
    assert r.status_code == 200, r.content
    employee.refresh_from_db()
    assert employee.first_name == "Paula" and employee.bio == "Especialista"


def test_profile_edit_unknown_and_forbidden(api, root_admin, verified_client, employee):
    assert api.patch(f"{BASE}/{uuid.uuid4()}/profile", {"first_name": "X"}, user=root_admin).status_code == 404
    assert api.patch(f"{BASE}/{employee.id}/profile", {"first_name": "X"}, user=verified_client).status_code == 403


def test_admin_uploads_employee_photo(api, manager_user, employee):
    r = api.post_form(f"{BASE}/{employee.id}/photo", {"photo": image_file()}, user=manager_user)
    assert r.status_code == 200, r.content
    assert api.post_form(f"{BASE}/{uuid.uuid4()}/photo", {"photo": image_file()}, user=manager_user).status_code == 404