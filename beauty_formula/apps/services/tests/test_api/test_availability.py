"""Disponibilidade pública: funcionários elegíveis, horários do dia e calendário do mês."""
import uuid
from datetime import timedelta

import pytest
from django.utils import timezone

from beauty_formula.apps.services.models.scheduling import Scheduling

pytestmark = pytest.mark.django_db

BASE = "/availability"


def _day(days_ahead=3):
    return (timezone.localdate() + timedelta(days=days_ahead)).isoformat()


def _month(days_ahead=3):
    """O parâmetro `month` é uma data (primeiro dia do mês)."""
    return (timezone.localdate() + timedelta(days=days_ahead)).replace(day=1).isoformat()


def test_eligible_employees_for_service(api, service, employee, employee_offers_service, open_all_week):
    r = api.get(f"{BASE}/eligible-employees/{service.id}")
    assert r.status_code == 200
    assert [e["id"] for e in r.json()] == [str(employee.id)]


def test_eligible_employees_unknown_service_is_404(api):
    assert api.get(f"{BASE}/eligible-employees/{uuid.uuid4()}").status_code == 404


def test_free_slots_for_a_day(api, service, employee, employee_offers_service, open_all_week):
    r = api.get(f"{BASE}/employee/{employee.id}", service_id=str(service.id), date=_day())
    assert r.status_code == 200, r.content
    assert len(r.json()["slots"] if isinstance(r.json(), dict) and "slots" in r.json() else r.json()) > 0


def test_booked_slot_disappears(api, service, employee, employee_offers_service, open_all_week, make_scheduling):
    day = _day(3)
    before = api.get(f"{BASE}/employee/{employee.id}", service_id=str(service.id), date=day).content
    make_scheduling(status=Scheduling.SchedulingStatus.CONFIRMED, days_ahead=3, hour=10)
    after = api.get(f"{BASE}/employee/{employee.id}", service_id=str(service.id), date=day).content
    assert before != after


def test_slots_unknown_employee_or_service_is_404(api, service, employee):
    assert api.get(f"{BASE}/employee/{uuid.uuid4()}", service_id=str(service.id), date=_day()).status_code == 404
    assert api.get(f"{BASE}/employee/{employee.id}", service_id=str(uuid.uuid4()), date=_day()).status_code == 404


def test_slots_require_query_params(api, employee):
    assert api.get(f"{BASE}/employee/{employee.id}").status_code == 422


def test_slots_for_past_date_are_empty_or_rejected(api, service, employee, employee_offers_service, open_all_week):
    r = api.get(f"{BASE}/employee/{employee.id}", service_id=str(service.id), date=(timezone.localdate() - timedelta(days=2)).isoformat())
    assert r.status_code in (200, 400)
    if r.status_code == 200:
        body = r.json()
        assert (body["slots"] if isinstance(body, dict) and "slots" in body else body) == []


def test_private_calendar_for_admin_and_manager(api, manager_user, root_admin, employee, employee_offers_service, open_all_week):
    for user in (manager_user, root_admin):
        r = api.get(f"{BASE}/employee/{employee.id}/calendar", user=user, month=_month())
        assert r.status_code == 200, r.content


def test_private_calendar_forbidden_for_client_employee_and_anonymous(api, verified_client, verified_employee, employee):
    assert api.get(f"{BASE}/employee/{employee.id}/calendar", user=verified_client, month=_month()).status_code == 403
    assert api.get(f"{BASE}/employee/{employee.id}/calendar", user=verified_employee, month=_month()).status_code == 403
    assert api.get(f"{BASE}/employee/{employee.id}/calendar", month=_month()).status_code == 401


def test_public_calendar(api, employee, employee_offers_service, open_all_week):
    r = api.get(f"{BASE}/employee/{employee.id}/public-calendar", month=_month())
    assert r.status_code == 200, r.content


@pytest.mark.parametrize("month", ["2026-13-01", "abc", "2026"])
def test_calendar_rejects_invalid_month(api, employee, month):
    assert api.get(f"{BASE}/employee/{employee.id}/public-calendar", month=month).status_code in (400, 422)