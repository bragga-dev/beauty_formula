"""Avaliações: cliente avalia atendimento concluído; admin/gerente moderam; leitura pública só do autorizado."""
import uuid

import pytest
from django.utils import timezone

from beauty_formula.apps.services.models.average_rating import AverageRating
from beauty_formula.apps.services.models.scheduling import Scheduling

pytestmark = pytest.mark.django_db

S = Scheduling.SchedulingStatus
BASE = "/average-ratings"


@pytest.fixture
def completed(make_scheduling):
    return make_scheduling(status=S.COMPLETED, days_ahead=-1, completed_at=timezone.now())


@pytest.fixture
def rated(api, verified_client, completed):
    r = api.post(f"{BASE}/create", {"scheduling_id": str(completed.id), "rating": 5, "comment": "Ótimo!"}, user=verified_client)
    assert r.status_code == 201, r.content
    return AverageRating.objects.get(id=r.json()["id"])


@pytest.fixture
def authorized(api, root_admin, rated):
    """Autoriza pela API: é o service que recalcula os agregados de média."""
    assert api.patch(f"{BASE}/admin/{rated.id}/authorize", user=root_admin).status_code in (200, 201)
    rated.refresh_from_db()
    return rated


# ── Criação ─────────────────────────────────────────────────────────────────

def test_client_rates_completed_scheduling(api, verified_client, completed, celery_delay):
    r = api.post(f"{BASE}/create", {"scheduling_id": str(completed.id), "rating": 4}, user=verified_client)
    assert r.status_code == 201, r.content
    rating = AverageRating.objects.get()
    assert rating.rating == 4 and rating.is_authorized is False
    completed.refresh_from_db()
    assert completed.rated_at is not None
    celery_delay.assert_called()  # admin é avisado da nova avaliação


def test_cannot_rate_twice_the_same_scheduling(api, verified_client, rated, completed):
    r = api.post(f"{BASE}/create", {"scheduling_id": str(completed.id), "rating": 1}, user=verified_client)
    assert r.status_code in (400, 409)
    assert AverageRating.objects.count() == 1


def test_cannot_rate_same_service_and_employee_again(api, verified_client, rated, make_scheduling):
    another = make_scheduling(status=S.COMPLETED, days_ahead=-2, completed_at=timezone.now())
    r = api.post(f"{BASE}/create", {"scheduling_id": str(another.id), "rating": 2}, user=verified_client)
    assert r.status_code in (400, 409)


def test_cannot_rate_unfinished_scheduling(api, verified_client, make_scheduling):
    pending = make_scheduling(status=S.CONFIRMED, days_ahead=3)
    r = api.post(f"{BASE}/create", {"scheduling_id": str(pending.id), "rating": 5}, user=verified_client)
    assert r.status_code in (400, 403, 404, 409)
    assert not AverageRating.objects.exists()


def test_cannot_rate_someone_elses_scheduling(api, other_verified_client, completed):
    r = api.post(f"{BASE}/create", {"scheduling_id": str(completed.id), "rating": 5}, user=other_verified_client)
    assert r.status_code in (403, 404)


@pytest.mark.parametrize("bad", [0, 6, -1])
def test_rating_must_be_between_1_and_5(api, verified_client, completed, bad):
    assert api.post(f"{BASE}/create", {"scheduling_id": str(completed.id), "rating": bad}, user=verified_client).status_code == 422


def test_unknown_scheduling_is_404(api, verified_client):
    assert api.post(f"{BASE}/create", {"scheduling_id": str(uuid.uuid4()), "rating": 5}, user=verified_client).status_code == 404


@pytest.mark.parametrize("who", ["verified_employee", "manager_user", "root_admin"])
def test_only_clients_create_ratings(api, request, completed, who):
    assert api.post(f"{BASE}/create", {"scheduling_id": str(completed.id), "rating": 5}, user=request.getfixturevalue(who)).status_code in (403, 404)


# ── Minhas avaliações ───────────────────────────────────────────────────────

def test_my_ratings_list_and_detail(api, verified_client, rated):
    assert api.get(f"{BASE}/my-ratings", user=verified_client).json()["total"] == 1
    r = api.get(f"{BASE}/my-ratings/{rated.id}", user=verified_client)
    assert r.status_code == 200 and r.json()["comment"] == "Ótimo!"


def test_cannot_see_others_rating(api, other_verified_client, rated):
    assert api.get(f"{BASE}/my-ratings", user=other_verified_client).json()["total"] == 0
    assert api.get(f"{BASE}/my-ratings/{rated.id}", user=other_verified_client).status_code == 404


def test_update_my_rating(api, verified_client, rated):
    r = api.patch(f"{BASE}/my-ratings/{rated.id}", {"rating": 3, "comment": "Mudei de opinião"}, user=verified_client)
    assert r.status_code == 200, r.content
    rated.refresh_from_db()
    assert rated.rating == 3 and rated.comment == "Mudei de opinião"


def test_update_unknown_or_foreign_rating_is_404(api, verified_client, other_verified_client, rated):
    assert api.patch(f"{BASE}/my-ratings/{uuid.uuid4()}", {"rating": 1}, user=verified_client).status_code == 404
    assert api.patch(f"{BASE}/my-ratings/{rated.id}", {"rating": 1}, user=other_verified_client).status_code == 404


def test_delete_my_rating(api, verified_client, rated):
    assert api.delete(f"{BASE}/my-ratings/{rated.id}", user=verified_client).status_code in (200, 204)
    assert not AverageRating.objects.exists()


def test_cannot_delete_foreign_rating(api, other_verified_client, rated):
    assert api.delete(f"{BASE}/my-ratings/{rated.id}", user=other_verified_client).status_code == 404
    assert AverageRating.objects.exists()


# ── Leitura pública (só avaliações autorizadas) ─────────────────────────────

def test_public_listings_hide_unauthorized(api, rated, service, employee):
    assert api.get(f"{BASE}/all").json()["total"] == 0
    assert api.get(f"{BASE}/service/{service.id}").json()["total"] == 0
    assert api.get(f"{BASE}/employee/{employee.id}").json()["total"] == 0


def test_public_listings_show_authorized(api, authorized, service, employee):
    assert api.get(f"{BASE}/all").json()["total"] == 1
    assert api.get(f"{BASE}/all", rating=5).json()["total"] == 1
    assert api.get(f"{BASE}/all", rating=1).json()["total"] == 0
    assert api.get(f"{BASE}/service/{service.id}").json()["total"] == 1
    assert api.get(f"{BASE}/employee/{employee.id}").json()["total"] == 1


def test_public_listings_unknown_ids_are_404(api):
    assert api.get(f"{BASE}/service/{uuid.uuid4()}").status_code == 404
    assert api.get(f"{BASE}/employee/{uuid.uuid4()}").status_code == 404
    assert api.get(f"{BASE}/service/{uuid.uuid4()}/summary").status_code == 404
    assert api.get(f"{BASE}/employee/{uuid.uuid4()}/summary").status_code == 404


def test_summaries(api, authorized, service, employee):
    s = api.get(f"{BASE}/service/{service.id}/summary")
    e = api.get(f"{BASE}/employee/{employee.id}/summary")
    assert s.status_code == 200 and e.status_code == 200
    for body in (s.json(), e.json()):
        assert float(body["average_rating"]) == 5.0 and body["total_reviews"] == 1


# ── Moderação (admin / gerente / funcionário só sobre si) ───────────────────

@pytest.mark.parametrize("who", ["root_admin", "manager_user"])
def test_admin_and_manager_list_all_ratings(api, request, rated, who):
    r = api.get(f"{BASE}/admin/list", user=request.getfixturevalue(who))
    assert r.status_code == 200 and r.json()["total"] == 1


def test_admin_list_filters(api, root_admin, rated, service):
    assert api.get(f"{BASE}/admin/list", user=root_admin, is_authorized="true").json()["total"] == 0
    assert api.get(f"{BASE}/admin/list", user=root_admin, is_authorized="false").json()["total"] == 1
    assert api.get(f"{BASE}/admin/list", user=root_admin, rating=1).json()["total"] == 0
    assert api.get(f"{BASE}/admin/list", user=root_admin, service_id=str(service.id)).json()["total"] == 1


def test_employee_lists_only_ratings_about_self(api, verified_employee, other_verified_employee, rated):
    assert api.get(f"{BASE}/admin/list", user=verified_employee).json()["total"] == 1
    assert api.get(f"{BASE}/admin/list", user=other_verified_employee).json()["total"] == 0


def test_client_cannot_use_admin_list(api, verified_client, rated):
    assert api.get(f"{BASE}/admin/list", user=verified_client).status_code == 403


def test_admin_detail(api, root_admin, rated):
    assert api.get(f"{BASE}/admin/{rated.id}", user=root_admin).status_code == 200
    assert api.get(f"{BASE}/admin/{uuid.uuid4()}", user=root_admin).status_code == 404


def test_employee_sees_detail_only_of_own_ratings(api, verified_employee, other_verified_employee, rated):
    assert api.get(f"{BASE}/admin/{rated.id}", user=verified_employee).status_code == 200
    assert api.get(f"{BASE}/admin/{rated.id}", user=other_verified_employee).status_code == 403


@pytest.mark.parametrize("who", ["root_admin", "manager_user"])
def test_authorize_and_revoke(api, request, rated, who):
    user = request.getfixturevalue(who)
    assert api.patch(f"{BASE}/admin/{rated.id}/authorize", user=user).status_code in (200, 201)
    rated.refresh_from_db()
    assert rated.is_authorized is True
    assert api.patch(f"{BASE}/admin/{rated.id}/revoke", user=user).status_code in (200, 201)
    rated.refresh_from_db()
    assert rated.is_authorized is False


def test_employee_authorizes_own_rating_but_not_others(api, verified_employee, other_verified_employee, rated):
    assert api.patch(f"{BASE}/admin/{rated.id}/authorize", user=other_verified_employee).status_code == 403
    rated.refresh_from_db()
    assert rated.is_authorized is False
    assert api.patch(f"{BASE}/admin/{rated.id}/authorize", user=verified_employee).status_code in (200, 201)


def test_employee_cannot_revoke_or_delete(api, verified_employee, authorized):
    assert api.patch(f"{BASE}/admin/{authorized.id}/revoke", user=verified_employee).status_code == 403
    assert api.delete(f"{BASE}/admin/{authorized.id}", user=verified_employee).status_code == 403


def test_authorize_unknown_is_404(api, root_admin):
    assert api.patch(f"{BASE}/admin/{uuid.uuid4()}/authorize", user=root_admin).status_code == 404
    assert api.patch(f"{BASE}/admin/{uuid.uuid4()}/revoke", user=root_admin).status_code == 404
    assert api.delete(f"{BASE}/admin/{uuid.uuid4()}", user=root_admin).status_code == 404


def test_admin_deletes_rating(api, manager_user, rated):
    assert api.delete(f"{BASE}/admin/{rated.id}", user=manager_user).status_code in (200, 204)
    assert not AverageRating.objects.exists()