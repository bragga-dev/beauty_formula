"""Formulário de contato (público) e gestão das mensagens (admin ou gerente)."""
import uuid

import pytest

from beauty_formula.apps.website.models.contact_models import Contact

pytestmark = pytest.mark.django_db

PAYLOAD = {"full_name": "Ana Souza", "subject": "question", "message": "Qual o horário?", "email": "ana@example.com", "phone": "(77) 99999-0000"}


@pytest.fixture
def contact(db):
    return Contact.objects.create(full_name="Bia", subject="complaint", message="Demorou", email="bia@example.com", phone="77999990000")


def test_public_create_contact(api):
    r = api.post("/contacts/create-contact", PAYLOAD)
    assert r.status_code == 201, r.content
    saved = Contact.objects.get(email="ana@example.com")
    assert saved.status == Contact.ContactStatus.PENDING and saved.subject == "question"


def test_create_defaults_subject_to_other(api):
    data = {k: v for k, v in PAYLOAD.items() if k != "subject"}
    assert api.post("/contacts/create-contact", data).status_code == 201
    assert Contact.objects.get().subject == Contact.ContactSubject.OTHER


@pytest.mark.parametrize("missing", ["full_name", "message", "email", "phone"])
def test_create_requires_fields(api, missing):
    data = {k: v for k, v in PAYLOAD.items() if k != missing}
    assert api.post("/contacts/create-contact", data).status_code == 422


def test_create_rejects_empty_message(api):
    assert api.post("/contacts/create-contact", {**PAYLOAD, "message": ""}).status_code == 422


def test_create_is_rate_limited(api):
    codes = [api.post("/contacts/create-contact", PAYLOAD).status_code for _ in range(7)]
    assert 429 in codes


@pytest.mark.parametrize("who", ["root_admin", "manager_user"])
def test_admin_and_manager_list_contacts(api, request, contact, who):
    r = api.get("/contacts/list-contacts", user=request.getfixturevalue(who))
    assert r.status_code == 200 and r.json()["total"] == 1


def test_list_filters(api, root_admin, contact):
    Contact.objects.create(full_name="Caio", subject="question", message="Oi", email="c@example.com", phone="1")
    assert api.get("/contacts/list-contacts", user=root_admin, subject="question").json()["total"] == 1
    assert api.get("/contacts/list-contacts", user=root_admin, status="resolved").json()["total"] == 0
    assert api.get("/contacts/list-contacts", user=root_admin, search="Bia").json()["total"] == 1


@pytest.mark.parametrize("who", ["verified_client", "verified_employee"])
def test_management_forbidden_for_client_and_employee(api, request, contact, who):
    user = request.getfixturevalue(who)
    assert api.get("/contacts/list-contacts", user=user).status_code == 403
    assert api.get(f"/contacts/detail-contact/{contact.id}", user=user).status_code == 403
    assert api.delete(f"/contacts/delete-contact/{contact.id}", user=user).status_code == 403


def test_management_requires_authentication(api, contact):
    assert api.get("/contacts/list-contacts").status_code == 401


def test_detail(api, root_admin, contact):
    r = api.get(f"/contacts/detail-contact/{contact.id}", user=root_admin)
    assert r.status_code == 200 and r.json()["email"] == "bia@example.com"


def test_detail_unknown_is_404(api, root_admin):
    assert api.get(f"/contacts/detail-contact/{uuid.uuid4()}", user=root_admin).status_code == 404


def test_update_status(api, manager_user, contact):
    r = api.patch(f"/contacts/update-contact-status/{contact.id}", {"status": "resolved"}, user=manager_user)
    assert r.status_code == 200 and r.json()["status"] == "resolved"
    contact.refresh_from_db()
    assert contact.status == Contact.ContactStatus.RESOLVED


def test_update_status_invalid_is_422(api, root_admin, contact):
    assert api.patch(f"/contacts/update-contact-status/{contact.id}", {"status": "xyz"}, user=root_admin).status_code == 422


def test_update_status_unknown_is_404(api, root_admin):
    assert api.patch(f"/contacts/update-contact-status/{uuid.uuid4()}", {"status": "resolved"}, user=root_admin).status_code == 404


def test_delete_contact(api, root_admin, contact):
    assert api.delete(f"/contacts/delete-contact/{contact.id}", user=root_admin).status_code == 200
    assert not Contact.objects.exists()


def test_delete_unknown_is_404(api, root_admin):
    assert api.delete(f"/contacts/delete-contact/{uuid.uuid4()}", user=root_admin).status_code == 404