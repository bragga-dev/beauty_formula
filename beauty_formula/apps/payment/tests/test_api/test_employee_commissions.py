"""Comissões: admin/gerente administram; o funcionário só lê as próprias."""
import uuid
from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils import timezone

from beauty_formula.apps.payment.models.employee_commission_model import EmployeeCommission
from beauty_formula.apps.services.models.scheduling import Scheduling

pytestmark = pytest.mark.django_db

S = Scheduling.SchedulingStatus
C = EmployeeCommission.CommissionStatus
BASE = "/commissions"


@pytest.fixture
def completed(make_scheduling):
    return make_scheduling(status=S.COMPLETED, days_ahead=-1, completed_at=timezone.now() - timedelta(hours=20))


@pytest.fixture
def client_login(client_profile):
    """Usuário do perfil de cliente (a fixture `verified_client` do payment/conftest usa outro e-mail e colide)."""
    user = client_profile.user
    user.is_trusty = True
    user.is_active = True
    user.save(update_fields=["is_trusty", "is_active"])
    return user


@pytest.fixture
def commission(api, root_admin, completed):
    r = api.post(f"{BASE}/create", {"scheduling_id": str(completed.id)}, user=root_admin)
    assert r.status_code == 201, r.content
    return EmployeeCommission.objects.get(id=r.json()["id"])


def _period(days=3):
    today = timezone.localdate()
    return {"start_date": (today - timedelta(days=days)).isoformat(), "end_date": (today + timedelta(days=1)).isoformat()}


# ── Criação / geração ───────────────────────────────────────────────────────

@pytest.mark.parametrize("who", ["root_admin", "manager_user"])
def test_create_commission_for_completed_scheduling(api, request, completed, service, who):
    r = api.post(f"{BASE}/create", {"scheduling_id": str(completed.id)}, user=request.getfixturevalue(who))
    assert r.status_code == 201, r.content
    c = EmployeeCommission.objects.get()
    expected = (service.price * service.commission_percentage / Decimal("100")).quantize(Decimal("0.01"))
    assert c.commission_value == expected and c.status == C.PENDING


def test_cannot_create_twice(api, root_admin, commission, completed):
    assert api.post(f"{BASE}/create", {"scheduling_id": str(completed.id)}, user=root_admin).status_code in (400, 409)
    assert EmployeeCommission.objects.count() == 1


def test_cannot_create_for_unfinished_scheduling(api, root_admin, make_scheduling):
    pending = make_scheduling(status=S.CONFIRMED, days_ahead=3)
    assert api.post(f"{BASE}/create", {"scheduling_id": str(pending.id)}, user=root_admin).status_code in (400, 409)
    assert not EmployeeCommission.objects.exists()


def test_create_unknown_scheduling_is_404(api, root_admin):
    assert api.post(f"{BASE}/create", {"scheduling_id": str(uuid.uuid4())}, user=root_admin).status_code == 404


def test_generate_period(api, root_admin, completed):
    r = api.post(f"{BASE}/generate-period", _period(), user=root_admin)
    assert r.status_code in (200, 201), r.content
    assert EmployeeCommission.objects.count() == 1


def test_generate_period_is_idempotent(api, root_admin, completed):
    api.post(f"{BASE}/generate-period", _period(), user=root_admin)
    api.post(f"{BASE}/generate-period", _period(), user=root_admin)
    assert EmployeeCommission.objects.count() == 1


def test_sync_creates_missing_commissions(api, root_admin, completed):
    r = api.post(f"{BASE}/sync", user=root_admin)
    assert r.status_code in (200, 201), r.content
    assert EmployeeCommission.objects.count() == 1


# ── Leitura (admin / gerente) ───────────────────────────────────────────────

@pytest.mark.parametrize("who", ["root_admin", "manager_user"])
def test_list_all_and_filters(api, request, commission, employee, who):
    user = request.getfixturevalue(who)
    assert api.get(f"{BASE}/list-all", user=user).json()["total"] == 1
    assert api.get(f"{BASE}/list-all", user=user, status="paid").json()["total"] == 0
    assert api.get(f"{BASE}/list-all", user=user, employee_id=str(employee.id)).json()["total"] == 1
    assert api.get(f"{BASE}/list-all", user=user, employee_id=str(uuid.uuid4())).json()["total"] == 0


def test_summary_and_competencias(api, root_admin, commission):
    assert api.get(f"{BASE}/summary", user=root_admin).status_code == 200
    r = api.get(f"{BASE}/competencias", user=root_admin)
    assert r.status_code == 200 and len(r.json()) == 1


def test_detail(api, root_admin, commission):
    assert api.get(f"{BASE}/{commission.id}", user=root_admin).status_code == 200
    assert api.get(f"{BASE}/{uuid.uuid4()}", user=root_admin).status_code == 404


@pytest.mark.parametrize("who", ["client_login", "verified_employee"])
def test_admin_routes_forbidden_for_client_and_employee(api, request, commission, who):
    user = request.getfixturevalue(who)
    assert api.get(f"{BASE}/list-all", user=user).status_code == 403
    assert api.post(f"{BASE}/sync", user=user).status_code == 403
    assert api.patch(f"{BASE}/mark-as-paid/{commission.id}", user=user).status_code == 403


# ── Alterações ──────────────────────────────────────────────────────────────

def test_update_value_while_pending(api, root_admin, commission):
    r = api.patch(f"{BASE}/update-value/{commission.id}", {"commission_value": "55.50"}, user=root_admin)
    assert r.status_code == 200, r.content
    commission.refresh_from_db()
    assert commission.commission_value == Decimal("55.50")


def test_update_value_unknown_is_404(api, root_admin):
    assert api.patch(f"{BASE}/update-value/{uuid.uuid4()}", {"commission_value": "1"}, user=root_admin).status_code == 404


def test_update_competencia(api, manager_user, commission):
    r = api.patch(f"{BASE}/update-competencia/{commission.id}", {"competencia": "2026-01-01"}, user=manager_user)
    assert r.status_code == 200, r.content
    commission.refresh_from_db()
    assert str(commission.competencia) == "2026-01-01"


@pytest.mark.xfail(strict=True, reason="mark_commission_as_paid grava `paid_by`, campo que não existe no model EmployeeCommission")
def test_mark_single_commission_as_paid(api, root_admin, commission):
    response = api.patch(f"{BASE}/mark-as-paid/{commission.id}",
        user=root_admin,
    )

    assert response.status_code == 200

    commission.refresh_from_db()

    assert commission.status == C.PAID
    assert commission.paid_at is not None
    assert commission.paid_by_id == root_admin.id

def test_mark_paid_revert_and_cancel_cycle(api, root_admin, commission):
    api.patch(f"{BASE}/mark-as-paid-bulk", {"commission_ids": [str(commission.id)]}, user=root_admin)
    commission.refresh_from_db()
    assert commission.status == C.PAID and commission.paid_at is not None

    assert api.patch(f"{BASE}/update-value/{commission.id}", {"commission_value": "1"}, user=root_admin).status_code in (400, 409)
    assert api.patch(f"{BASE}/cancel/{commission.id}", user=root_admin).status_code in (400, 409)

    assert api.patch(f"{BASE}/revert-to-pending/{commission.id}", user=root_admin).status_code == 200
    commission.refresh_from_db()
    assert commission.status == C.PENDING

    assert api.patch(f"{BASE}/cancel/{commission.id}", user=root_admin).status_code == 200
    commission.refresh_from_db()
    assert commission.status == C.CANCELED


def test_revert_requires_paid(api, root_admin, commission):
    assert api.patch(f"{BASE}/revert-to-pending/{commission.id}", user=root_admin).status_code in (400, 409)


def test_state_changes_on_unknown_are_404(api, root_admin):
    ghost = uuid.uuid4()
    for route in ("mark-as-paid", "cancel", "revert-to-pending"):
        assert api.patch(f"{BASE}/{route}/{ghost}", user=root_admin).status_code == 404


def test_bulk_mark_as_paid_skips_unknown(api, root_admin, commission):
    ghost = uuid.uuid4()
    r = api.patch(f"{BASE}/mark-as-paid-bulk", {"commission_ids": [str(commission.id), str(ghost)]}, user=root_admin)
    assert r.status_code == 200, r.content
    body = r.json()
    assert body["updated_count"] == 1 and body["skipped_ids"] == [str(ghost)]


def test_update_status_for_period(api, root_admin, commission):
    r = api.patch(f"{BASE}/update-status-period", {**_period(), "status": "paid"}, user=root_admin)
    assert r.status_code == 200, r.content
    assert r.json()["updated_count"] == 1
    commission.refresh_from_db()
    assert commission.status == C.PAID


# ── Funcionário: só as próprias ─────────────────────────────────────────────

def test_employee_lists_own_commissions_only(api, verified_employee, other_verified_employee, commission):
    assert api.get(f"{BASE}/my-commissions/list", user=verified_employee).json()["total"] == 1
    assert api.get(f"{BASE}/my-commissions/list", user=other_verified_employee).json()["total"] == 0


def test_employee_summary(api, verified_employee, commission):
    assert api.get(f"{BASE}/my-commissions/summary", user=verified_employee).status_code == 200


def test_employee_detail_own_vs_foreign(api, verified_employee, other_verified_employee, commission):
    assert api.get(f"{BASE}/my-commissions/{commission.id}", user=verified_employee).status_code == 200
    assert api.get(f"{BASE}/my-commissions/{commission.id}", user=other_verified_employee).status_code == 404


@pytest.mark.parametrize("who", ["client_login", "manager_user", "root_admin"])
def test_my_commissions_is_employee_only(api, request, who):
    assert api.get(f"{BASE}/my-commissions/list", user=request.getfixturevalue(who)).status_code in (403, 404)