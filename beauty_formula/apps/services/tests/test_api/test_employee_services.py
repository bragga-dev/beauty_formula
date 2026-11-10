"""Vínculo funcionário ↔ serviço (o funcionário escolhe o que oferece)."""
import uuid

import pytest

from beauty_formula.apps.services.models.employee_service import EmployeeService

pytestmark = pytest.mark.django_db

BASE = "/employee-services/"


def test_employee_offers_a_service(api, verified_employee, employee, service):
    r = api.post(f"{BASE}create-employee-service", {"service_id": str(service.id)}, user=verified_employee)
    assert r.status_code == 201, r.content
    assert EmployeeService.objects.filter(employee=employee, service=service, is_active=True).exists()


def test_cannot_offer_same_service_twice(api, verified_employee, service, employee_offers_service):
    r = api.post(f"{BASE}create-employee-service", {"service_id": str(service.id)}, user=verified_employee)
    assert r.status_code in (400, 409)
    assert EmployeeService.objects.count() == 1


def test_cannot_offer_unknown_service(api, verified_employee):
    assert api.post(f"{BASE}create-employee-service", {"service_id": str(uuid.uuid4())}, user=verified_employee).status_code in (400, 404)


def test_list_my_services(api, verified_employee, employee_offers_service):
    r = api.get(f"{BASE}list-my-services", user=verified_employee)
    assert r.status_code == 200 and r.json()["total"] == 1


def test_list_active_only(api, verified_employee, employee_offers_service):
    employee_offers_service.is_active = False
    employee_offers_service.save(update_fields=["is_active"])
    assert api.get(f"{BASE}list-my-services", user=verified_employee, active_only="true").json()["total"] == 0
    assert api.get(f"{BASE}list-my-services", user=verified_employee, active_only="false").json()["total"] == 1


def test_deactivate_and_activate(api, verified_employee, employee_offers_service):
    es = employee_offers_service
    assert api.patch(f"{BASE}deactivate-employee-service/{es.id}", user=verified_employee).status_code in (200, 201)
    es.refresh_from_db()
    assert es.is_active is False
    assert api.patch(f"{BASE}activate-employee-service/{es.id}", user=verified_employee).status_code in (200, 201)
    es.refresh_from_db()
    assert es.is_active is True


def test_delete_employee_service(api, verified_employee, employee_offers_service):
    assert api.delete(f"{BASE}delete-employee-service/{employee_offers_service.id}", user=verified_employee).status_code in (200, 204)
    assert not EmployeeService.objects.exists()


def test_unknown_employee_service_is_404(api, verified_employee):
    ghost = uuid.uuid4()
    assert api.patch(f"{BASE}activate-employee-service/{ghost}", user=verified_employee).status_code == 404
    assert api.patch(f"{BASE}deactivate-employee-service/{ghost}", user=verified_employee).status_code == 404
    assert api.delete(f"{BASE}delete-employee-service/{ghost}", user=verified_employee).status_code == 404


def test_cannot_touch_other_employees_link(api, other_verified_employee, employee_offers_service):
    es = employee_offers_service
    assert api.patch(f"{BASE}deactivate-employee-service/{es.id}", user=other_verified_employee).status_code in (403, 404)
    assert api.delete(f"{BASE}delete-employee-service/{es.id}", user=other_verified_employee).status_code in (403, 404)
    es.refresh_from_db()
    assert es.is_active is True


@pytest.mark.parametrize("who", ["verified_client", "manager_user", "root_admin"])
def test_only_employees_manage_links(api, request, service, who):
    user = request.getfixturevalue(who)
    assert api.get(f"{BASE}list-my-services", user=user).status_code in (403, 404)
    assert api.post(f"{BASE}create-employee-service", {"service_id": str(service.id)}, user=user).status_code in (403, 404)