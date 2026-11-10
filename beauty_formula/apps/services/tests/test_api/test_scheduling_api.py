"""Agendamento via API: criação, conflitos, janela, permissões e cancelamento."""
from datetime import timedelta

import pytest
from django.utils import timezone

from beauty_formula.apps.conftest import next_slot
from beauty_formula.apps.services.models.scheduling import Scheduling

pytestmark = pytest.mark.django_db


@pytest.fixture
def setup(employee_offers_service, open_all_week):
    return employee_offers_service


def _payload(employee, service, when, **extra):
    return {"service_id": str(service.id), "employee_id": str(employee.id), "scheduled_time": when.isoformat(), **extra}


def _create(api, user, employee, service, when):
    return api.post("/scheduling/create", _payload(employee, service, when), user=user)


def test_create_ok_snapshots_price_and_duration(api, verified_client, employee, service, setup):
    r = _create(api, verified_client, employee, service, next_slot())
    assert r.status_code == 201, r.content
    s = Scheduling.objects.get()
    assert s.price_at_booking == service.price and s.duration_at_booking == service.duration
    assert s.status == Scheduling.SchedulingStatus.CREATED


def test_create_in_the_past_is_rejected(api, verified_client, employee, service, setup):
    r = _create(api, verified_client, employee, service, timezone.now() - timedelta(hours=2))
    assert r.status_code == 422


def test_create_outside_working_hours_is_rejected(api, verified_client, employee, service, setup):
    r = _create(api, verified_client, employee, service, next_slot(hour=22))
    assert r.status_code in (400, 409)
    assert not Scheduling.objects.exists()


def _confirm_first():
    s = Scheduling.objects.get()
    s.confirm()
    return s


def test_unpaid_reservation_does_not_block_the_slot(api, verified_client, other_verified_client, employee, service, setup):
    """Desenho atual: só CONFIRMED ocupa a agenda; o conflito é resolvido no pagamento (com reembolso)."""
    assert _create(api, verified_client, employee, service, next_slot()).status_code == 201
    assert _create(api, other_verified_client, employee, service, next_slot()).status_code == 201


def test_create_conflicting_slot_is_rejected(api, verified_client, other_verified_client, employee, service, setup):
    assert _create(api, verified_client, employee, service, next_slot()).status_code == 201
    _confirm_first()
    r = _create(api, other_verified_client, employee, service, next_slot())
    assert r.status_code in (400, 409)
    assert Scheduling.objects.count() == 1


def test_create_overlapping_slot_is_rejected(api, verified_client, other_verified_client, employee, service, setup):
    _create(api, verified_client, employee, service, next_slot(hour=10))
    _confirm_first()
    r = _create(api, other_verified_client, employee, service, next_slot(hour=10) + timedelta(minutes=30))
    assert r.status_code in (400, 409)


def test_adjacent_slot_is_allowed(api, verified_client, other_verified_client, employee, service, setup):
    _create(api, verified_client, employee, service, next_slot(hour=10))
    _confirm_first()
    assert _create(api, other_verified_client, employee, service, next_slot(hour=11)).status_code == 201


def test_employee_that_does_not_offer_service_is_rejected(api, verified_client, employee, service, open_all_week):
    r = _create(api, verified_client, employee, service, next_slot())
    assert r.status_code in (400, 404)


def test_inactive_service_is_rejected(api, verified_client, employee, service, setup):
    service.is_active = False
    service.save()
    assert _create(api, verified_client, employee, service, next_slot()).status_code in (400, 404)


def test_booking_beyond_employee_window_is_rejected(api, verified_client, employee, service, setup):
    employee.booking_window_days = 7
    employee.save()
    r = _create(api, verified_client, employee, service, next_slot(days_ahead=40))
    assert r.status_code in (400, 409, 422)
    assert not Scheduling.objects.exists()


def test_booking_inside_window_is_allowed(api, verified_client, employee, service, setup):
    employee.booking_window_days = 7
    employee.save()
    assert _create(api, verified_client, employee, service, next_slot(days_ahead=3)).status_code == 201


def test_employee_cannot_create_scheduling(api, verified_employee, employee, service, setup):
    assert _create(api, verified_employee, employee, service, next_slot()).status_code == 403


# ── Ownership (IDOR) ────────────────────────────────────────────────────────

@pytest.fixture
def booked(api, verified_client, employee, service, setup):
    _create(api, verified_client, employee, service, next_slot())
    return Scheduling.objects.get()


def test_client_sees_only_own_schedulings(api, verified_client, other_verified_client, booked):
    mine = api.get("/scheduling/list-my-schedulings", user=verified_client).json()
    theirs = api.get("/scheduling/list-my-schedulings", user=other_verified_client).json()
    assert len(mine["items"] if isinstance(mine, dict) else mine) == 1
    assert len(theirs["items"] if isinstance(theirs, dict) else theirs) == 0


def test_client_cannot_read_someone_elses_scheduling(api, other_verified_client, booked):
    assert api.get(f"/scheduling/my-schedulings/{booked.id}", user=other_verified_client).status_code in (403, 404)


def test_client_cannot_cancel_someone_elses_scheduling(api, other_verified_client, booked):
    r = api.patch(f"/scheduling/cancel-my-scheduling/{booked.id}", {"reason": "teste"}, user=other_verified_client)
    assert r.status_code in (403, 404)
    booked.refresh_from_db()
    assert booked.status != Scheduling.SchedulingStatus.CANCELED


def test_other_employee_cannot_complete_scheduling(api, other_verified_employee, booked):
    r = api.patch(f"/scheduling/complete/{booked.id}", user=other_verified_employee)
    assert r.status_code in (403, 404)
    booked.refresh_from_db()
    assert booked.status != Scheduling.SchedulingStatus.COMPLETED


def test_client_cancels_own(api, verified_client, booked):
    r = api.patch(f"/scheduling/cancel-my-scheduling/{booked.id}", {"reason": "Imprevisto"}, user=verified_client)
    assert r.status_code == 200, r.content
    booked.refresh_from_db()
    assert booked.status == Scheduling.SchedulingStatus.CANCELED


def test_canceled_slot_can_be_rebooked(api, verified_client, other_verified_client, employee, service, booked):
    api.patch(f"/scheduling/cancel-my-scheduling/{booked.id}", {"reason": "x"}, user=verified_client)
    assert _create(api, other_verified_client, employee, service, next_slot()).status_code == 201


def test_cannot_complete_future_or_unconfirmed_scheduling(api, verified_employee, booked):
    r = api.patch(f"/scheduling/complete/{booked.id}", user=verified_employee)
    assert r.status_code in (400, 409)
    booked.refresh_from_db()
    assert booked.status == Scheduling.SchedulingStatus.CREATED


def test_admin_and_manager_can_list_all(api, root_admin, manager_user, booked):
    for u in (root_admin, manager_user):
        assert api.get("/scheduling/list-all", user=u).status_code == 200