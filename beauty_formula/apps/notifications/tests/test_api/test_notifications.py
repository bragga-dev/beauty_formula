"""Notificações do usuário logado e listagem administrativa."""
import uuid

import pytest

from beauty_formula.apps.notifications.models.notification import Notification
from beauty_formula.apps.notifications.services.notification_service import notify_system

pytestmark = pytest.mark.django_db


@pytest.fixture
def mine(verified_client):
    return [notify_system(user_id=verified_client.id, title=f"Aviso {i}", body="corpo") for i in range(3)]


@pytest.fixture
def others(other_verified_client):
    return notify_system(user_id=other_verified_client.id, title="De outro usuário")


def test_list_returns_only_my_notifications(api, verified_client, mine, others):
    r = api.get("/notifications/", user=verified_client)
    assert r.status_code == 200
    assert r.json()["total"] == 3


def test_list_unread_only(api, verified_client, mine):
    api.post(f"/notifications/{mine[0].id}/read/", user=verified_client)
    assert api.get("/notifications/", user=verified_client, unread_only="true").json()["total"] == 2


def test_unread_count(api, verified_client, mine):
    assert api.get("/notifications/unread-count/", user=verified_client).json()["unread_count"] == 3


def test_mark_one_as_read(api, verified_client, mine):
    r = api.post(f"/notifications/{mine[0].id}/read/", user=verified_client)
    assert r.status_code in (200, 201)
    mine[0].refresh_from_db()
    assert mine[0].is_read is True


def test_cannot_read_someone_elses_notification(api, verified_client, others):
    assert api.post(f"/notifications/{others.id}/read/", user=verified_client).status_code == 403
    others.refresh_from_db()
    assert others.is_read is False


def test_mark_unknown_is_404(api, verified_client):
    assert api.post(f"/notifications/{uuid.uuid4()}/read/", user=verified_client).status_code == 404


def test_read_all(api, verified_client, mine, others):
    r = api.post("/notifications/read-all/", user=verified_client)
    assert r.status_code in (200, 201)
    assert Notification.objects.filter(recipient=verified_client, is_read=False).count() == 0
    others.refresh_from_db()
    assert others.is_read is False


def test_delete_my_notification(api, verified_client, mine):
    r = api.delete(f"/notifications/{mine[0].id}/", user=verified_client)
    assert r.status_code in (200, 204)
    assert not Notification.objects.filter(id=mine[0].id).exists()


def test_cannot_delete_someone_elses_notification(api, verified_client, others):
    assert api.delete(f"/notifications/{others.id}/", user=verified_client).status_code == 403
    assert Notification.objects.filter(id=others.id).exists()


def test_notifications_require_authentication(api):
    assert api.get("/notifications/").status_code == 401
    assert api.get("/notifications/unread-count/").status_code == 401


@pytest.mark.parametrize("who", ["root_admin", "manager_user"])
def test_admin_and_manager_list_all(api, request, mine, others, who):
    r = api.get("/notifications/admin/list-all", user=request.getfixturevalue(who))
    assert r.status_code == 200 and r.json()["total"] == 4


def test_admin_list_filters_by_user_and_read(api, root_admin, verified_client, mine, others):
    assert api.get("/notifications/admin/list-all", user=root_admin, user_id=str(verified_client.id)).json()["total"] == 3
    api.post(f"/notifications/{mine[0].id}/read/", user=verified_client)
    assert api.get("/notifications/admin/list-all", user=root_admin, read="true").json()["total"] == 1


@pytest.mark.parametrize("who", ["verified_client", "verified_employee"])
def test_admin_list_forbidden_for_client_and_employee(api, request, who):
    assert api.get("/notifications/admin/list-all", user=request.getfixturevalue(who)).status_code == 403