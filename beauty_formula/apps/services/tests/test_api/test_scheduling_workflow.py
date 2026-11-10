"""Ciclo de vida do agendamento: cancelar, concluir, no-show, editar, remarcar, listar, excluir."""
import uuid
from datetime import timedelta

import pytest
from django.utils import timezone

from beauty_formula.apps.conftest import next_slot
from beauty_formula.apps.services.models.scheduling import Scheduling

pytestmark = pytest.mark.django_db

S = Scheduling.SchedulingStatus
BASE = "/scheduling"


@pytest.fixture
def setup(employee_offers_service, open_all_week):
    return employee_offers_service


@pytest.fixture
def created(make_scheduling):
    return make_scheduling(status=S.CREATED)


@pytest.fixture
def confirmed(make_scheduling):
    return make_scheduling(status=S.CONFIRMED, days_ahead=3)


@pytest.fixture
def finished(make_scheduling):
    """CONFIRMED e já encerrado (ontem): apto a concluir / no-show."""
    return make_scheduling(status=S.CONFIRMED, days_ahead=-1)


# ── Cancelamento ────────────────────────────────────────────────────────────

def test_client_cancels_created_anytime(api, verified_client, created):
    r = api.patch(f"{BASE}/cancel-my-scheduling/{created.id}", {"reason": "mudei de ideia"}, user=verified_client)
    assert r.status_code == 200, r.content
    created.refresh_from_db()
    assert created.status == S.CANCELED and created.canceled_reason == "mudei de ideia" and created.is_active is False


def test_client_cancels_confirmed_with_enough_notice(api, verified_client, confirmed):
    assert api.patch(f"{BASE}/cancel-my-scheduling/{confirmed.id}", {"reason": "imprevisto"}, user=verified_client).status_code == 200


def test_client_cannot_cancel_confirmed_within_2h(api, verified_client, make_scheduling):
    soon = make_scheduling(status=S.CONFIRMED, days_ahead=0, scheduled_time=timezone.now() + timedelta(minutes=30))
    r = api.patch(f"{BASE}/cancel-my-scheduling/{soon.id}", {"reason": "x"}, user=verified_client)
    assert r.status_code in (400, 403, 409)
    soon.refresh_from_db()
    assert soon.status == S.CONFIRMED


def test_client_cancel_requires_reason(api, verified_client, created):
    assert api.patch(f"{BASE}/cancel-my-scheduling/{created.id}", {}, user=verified_client).status_code == 422


def test_cancel_unknown_is_404(api, verified_client):
    assert api.patch(f"{BASE}/cancel-my-scheduling/{uuid.uuid4()}", {"reason": "x"}, user=verified_client).status_code == 404


def test_cannot_cancel_twice(api, verified_client, created):
    api.patch(f"{BASE}/cancel-my-scheduling/{created.id}", {"reason": "a"}, user=verified_client)
    assert api.patch(f"{BASE}/cancel-my-scheduling/{created.id}", {"reason": "b"}, user=verified_client).status_code in (400, 409)


def test_employee_cancels_own_scheduling(api, verified_employee, confirmed):
    r = api.patch(f"{BASE}/cancel-employee-scheduling/{confirmed.id}", {"reason": "doente"}, user=verified_employee)
    assert r.status_code == 200, r.content
    confirmed.refresh_from_db()
    assert confirmed.status == S.CANCELED


def test_employee_cannot_cancel_someone_elses(api, other_verified_employee, confirmed):
    r = api.patch(f"{BASE}/cancel-employee-scheduling/{confirmed.id}", {"reason": "x"}, user=other_verified_employee)
    assert r.status_code in (403, 404)
    confirmed.refresh_from_db()
    assert confirmed.status == S.CONFIRMED


@pytest.mark.parametrize("who", ["root_admin", "manager_user"])
def test_admin_and_manager_cancel_any(api, request, confirmed, who):
    r = api.patch(f"{BASE}/cancel/{confirmed.id}", {"reason": "administrativo"}, user=request.getfixturevalue(who))
    assert r.status_code == 200, r.content
    confirmed.refresh_from_db()
    assert confirmed.status == S.CANCELED


@pytest.mark.parametrize("who", ["verified_client", "verified_employee"])
def test_admin_cancel_forbidden_for_others(api, request, confirmed, who):
    assert api.patch(f"{BASE}/cancel/{confirmed.id}", {"reason": "x"}, user=request.getfixturevalue(who)).status_code == 403


# ── Concluir / no-show ──────────────────────────────────────────────────────

def test_employee_completes_finished_scheduling(api, verified_employee, finished):
    r = api.patch(f"{BASE}/complete/{finished.id}", user=verified_employee)
    assert r.status_code == 200, r.content
    finished.refresh_from_db()
    assert finished.status == S.COMPLETED and finished.completed_at is not None


def test_employee_marks_no_show(api, verified_employee, finished):
    r = api.patch(f"{BASE}/no-show/{finished.id}", user=verified_employee)
    assert r.status_code == 200, r.content
    finished.refresh_from_db()
    assert finished.status == S.NO_SHOW and finished.is_active is False


def test_cannot_complete_twice(api, verified_employee, finished):
    api.patch(f"{BASE}/complete/{finished.id}", user=verified_employee)
    assert api.patch(f"{BASE}/complete/{finished.id}", user=verified_employee).status_code in (400, 409)


def test_complete_unknown_is_404(api, verified_employee):
    assert api.patch(f"{BASE}/complete/{uuid.uuid4()}", user=verified_employee).status_code == 404


@pytest.mark.parametrize("who", ["verified_client", "manager_user"])
def test_complete_and_no_show_are_employee_only(api, request, finished, who):
    user = request.getfixturevalue(who)
    assert api.patch(f"{BASE}/complete/{finished.id}", user=user).status_code in (403, 404)
    assert api.patch(f"{BASE}/no-show/{finished.id}", user=user).status_code in (403, 404)


# ── Atualizar / remarcar ────────────────────────────────────────────────────

def test_client_updates_notes_of_created(api, verified_client, created):
    r = api.patch(f"{BASE}/update-my-scheduling/{created.id}", {"notes": "alergia a amônia"}, user=verified_client)
    assert r.status_code == 200, r.content
    created.refresh_from_db()
    assert created.notes == "alergia a amônia"


def test_client_cannot_update_someone_elses(api, other_verified_client, created):
    assert api.patch(f"{BASE}/update-my-scheduling/{created.id}", {"notes": "x"}, user=other_verified_client).status_code in (403, 404)


def test_client_reschedules_confirmed(api, verified_client, confirmed, setup):
    new_time = next_slot(days_ahead=5, hour=14)
    r = api.patch(f"{BASE}/reschedule-my-scheduling/{confirmed.id}", {"scheduled_time": new_time.isoformat()}, user=verified_client)
    assert r.status_code == 200, r.content
    confirmed.refresh_from_db()
    assert confirmed.status == S.RESCHEDULED and confirmed.rescheduled_to is not None
    assert confirmed.rescheduled_to.scheduled_time == new_time


def test_cannot_reschedule_unconfirmed(api, verified_client, created, setup):
    r = api.patch(f"{BASE}/reschedule-my-scheduling/{created.id}", {"scheduled_time": next_slot(5).isoformat()}, user=verified_client)
    assert r.status_code in (400, 409)


def test_reschedule_into_the_past_is_rejected(api, verified_client, confirmed, setup):
    r = api.patch(f"{BASE}/reschedule-my-scheduling/{confirmed.id}", {"scheduled_time": (timezone.now() - timedelta(days=1)).isoformat()}, user=verified_client)
    assert r.status_code in (400, 422)


@pytest.mark.parametrize("who", ["root_admin", "manager_user"])
def test_admin_updates_any_scheduling(api, request, created, who):
    r = api.patch(f"{BASE}/update/{created.id}", {"notes": "ajuste interno"}, user=request.getfixturevalue(who))
    assert r.status_code == 200, r.content
    created.refresh_from_db()
    assert created.notes == "ajuste interno"


def test_admin_update_unknown_is_404(api, root_admin):
    assert api.patch(f"{BASE}/update/{uuid.uuid4()}", {"notes": "x"}, user=root_admin).status_code == 404


# ── Leitura ─────────────────────────────────────────────────────────────────

def test_client_detail_of_own(api, verified_client, created):
    r = api.get(f"{BASE}/my-schedulings/{created.id}", user=verified_client)
    assert r.status_code == 200 and r.json()["id"] == str(created.id)


def test_client_list_active_only(api, verified_client, created, make_scheduling):
    make_scheduling(status=S.CANCELED, is_active=False, days_ahead=4, canceled_at=timezone.now(), canceled_reason="x")
    assert api.get(f"{BASE}/list-my-schedulings", user=verified_client).json()["total"] == 2
    assert api.get(f"{BASE}/list-my-schedulings", user=verified_client, active_only="true").json()["total"] == 1


def test_employee_lists_and_reads_own_schedulings(api, verified_employee, other_verified_employee, created):
    assert api.get(f"{BASE}/list-employee-schedulings", user=verified_employee).json()["total"] == 1
    assert api.get(f"{BASE}/list-employee-schedulings", user=other_verified_employee).json()["total"] == 0
    assert api.get(f"{BASE}/employee-schedulings/{created.id}", user=verified_employee).status_code == 200
    assert api.get(f"{BASE}/employee-schedulings/{created.id}", user=other_verified_employee).status_code in (403, 404)


def test_list_all_filters(api, root_admin, created, confirmed, service, employee):
    assert api.get(f"{BASE}/list-all", user=root_admin).json()["total"] == 2
    assert api.get(f"{BASE}/list-all", user=root_admin, status="confirmed").json()["total"] == 1
    assert api.get(f"{BASE}/list-all", user=root_admin, service_id=str(service.id)).json()["total"] == 2
    assert api.get(f"{BASE}/list-all", user=root_admin, employee_id=str(uuid.uuid4())).json()["total"] == 0
    start = (confirmed.scheduled_time - timedelta(hours=1)).isoformat()
    end = (confirmed.scheduled_time + timedelta(hours=1)).isoformat()
    assert api.get(f"{BASE}/list-all", user=root_admin, start_date=start, end_date=end).json()["total"] == 1


def test_admin_detail_and_unknown(api, manager_user, created):
    assert api.get(f"{BASE}/{created.id}", user=manager_user).status_code == 200
    assert api.get(f"{BASE}/{uuid.uuid4()}", user=manager_user).status_code == 404


def test_admin_deletes_scheduling(api, root_admin, created):
    assert api.delete(f"{BASE}/{created.id}", user=root_admin).status_code in (200, 204)
    assert not Scheduling.objects.filter(id=created.id).exists()


def test_delete_unknown_is_404(api, root_admin):
    assert api.delete(f"{BASE}/{uuid.uuid4()}", user=root_admin).status_code == 404


@pytest.mark.parametrize("who", ["verified_client", "verified_employee"])
def test_admin_routes_forbidden_for_client_and_employee(api, request, created, who):
    user = request.getfixturevalue(who)
    assert api.get(f"{BASE}/list-all", user=user).status_code == 403
    assert api.get(f"{BASE}/{created.id}", user=user).status_code == 403
    assert api.delete(f"{BASE}/{created.id}", user=user).status_code == 403