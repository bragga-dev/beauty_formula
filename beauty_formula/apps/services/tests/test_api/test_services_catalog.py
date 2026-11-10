"""Catálogo de serviços: leitura pública; escrita para admin ou gerente."""
import json
import uuid
from datetime import timedelta
from decimal import Decimal

import pytest

from beauty_formula.apps.conftest import image_file
from beauty_formula.apps.services.models.service import Service

pytestmark = pytest.mark.django_db


@pytest.fixture
def inactive_service(db):
    return Service.objects.create(name="Escova", price=Decimal("80.00"), duration=timedelta(minutes=45), is_active=False)


def _payload(**extra):
    return {"payload": json.dumps({"name": "Hidratação", "description": "Profunda", "price": "120.00", "duration_minutes": 90, **extra})}


def test_public_list_shows_only_active(api, service, inactive_service):
    r = api.get("/services/list-services")
    assert r.status_code == 200
    assert [i["name"] for i in r.json()["items"]] == ["Corte"]


def test_private_list_for_admin_and_manager(api, root_admin, manager_user, service, inactive_service):
    for user in (root_admin, manager_user):
        assert api.get("/services/list-private-services", user=user).json()["total"] == 2


@pytest.mark.parametrize("who", ["verified_client", "verified_employee"])
def test_private_list_forbidden(api, request, who):
    assert api.get("/services/list-private-services", user=request.getfixturevalue(who)).status_code == 403


def test_detail_is_public_and_exposes_duration(api, service):
    r = api.get(f"/services/detail-service/{service.id}")
    assert r.status_code == 200 and r.json()["duration_minutes"] == 60


def test_detail_unknown_is_404(api):
    assert api.get(f"/services/detail-service/{uuid.uuid4()}").status_code == 404


@pytest.mark.parametrize("who", ["root_admin", "manager_user"])
def test_create_service(api, request, who):
    r = api.post_form("/services/create-service", _payload(), user=request.getfixturevalue(who))
    assert r.status_code == 201, r.content
    s = Service.objects.get(name="Hidratação")
    assert s.duration == timedelta(minutes=90) and s.price == Decimal("120.00")


def test_create_service_with_image(api, root_admin):
    r = api.post_form("/services/create-service", {**_payload(), "image": image_file()}, user=root_admin)
    assert r.status_code == 201, r.content


@pytest.mark.parametrize("bad", [{"price": "-1"}, {"commission_percentage": "150"}, {"duration_minutes": 0}, {"name": ""}])
def test_create_rejects_invalid_values(api, root_admin, bad):
    r = api.post_form("/services/create-service", _payload(**bad), user=root_admin)
    assert r.status_code in (400, 422)
    assert not Service.objects.filter(name="Hidratação").exists()


def test_create_duplicate_name_is_400(api, root_admin, service):
    assert api.post_form("/services/create-service", _payload(name="Corte"), user=root_admin).status_code == 400


@pytest.mark.parametrize("who", ["verified_client", "verified_employee"])
def test_write_forbidden_for_client_and_employee(api, request, service, who):
    user = request.getfixturevalue(who)
    assert api.post_form("/services/create-service", _payload(), user=user).status_code == 403
    assert api.patch(f"/services/update-service/{service.id}", {"price": "1"}, user=user).status_code == 403
    assert api.delete(f"/services/delete-service/{service.id}", user=user).status_code == 403


def test_update_service(api, root_admin, service):
    r = api.patch(f"/services/update-service/{service.id}", {"price": "150.00", "duration_minutes": 30}, user=root_admin)
    assert r.status_code == 200, r.content
    service.refresh_from_db()
    assert service.price == Decimal("150.00") and service.duration == timedelta(minutes=30) and service.name == "Corte"


def test_update_unknown_is_404(api, root_admin):
    assert api.patch(f"/services/update-service/{uuid.uuid4()}", {"price": "1"}, user=root_admin).status_code == 404


def test_update_image(api, manager_user, service):
    assert api.patch_form(f"/services/update-image-service/{service.id}", {"image": image_file()}, user=manager_user).status_code == 200


def test_deactivate_and_activate(api, root_admin, service):
    assert api.patch(f"/services/deactivate-service/{service.id}", user=root_admin).status_code in (200, 201)
    service.refresh_from_db()
    assert service.is_active is False
    assert api.get("/services/list-services").json()["total"] == 0
    assert api.patch(f"/services/activate-service/{service.id}", user=root_admin).status_code in (200, 201)
    service.refresh_from_db()
    assert service.is_active is True


def test_delete_service(api, root_admin, service):
    assert api.delete(f"/services/delete-service/{service.id}", user=root_admin).status_code == 200
    assert not Service.objects.filter(id=service.id).exists()


def test_delete_unknown_is_404(api, root_admin):
    assert api.delete(f"/services/delete-service/{uuid.uuid4()}", user=root_admin).status_code == 404