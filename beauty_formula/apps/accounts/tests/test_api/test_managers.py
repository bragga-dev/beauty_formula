"""CRUD de gerente: cadastro exclusivo do admin root; demais rotas para admin ou gerente."""
import uuid

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from beauty_formula.apps.accounts.models import User
from beauty_formula.apps.accounts.models.manager import DEFAULT_MANAGER_PHOTO, Manager
from beauty_formula.apps.conftest import image_file

pytestmark = pytest.mark.django_db

NEW = {"email": "novo.gerente@example.com", "first_name": "Nina", "last_name": "Gestora"}


@pytest.fixture
def other_manager(db):
    user = User.objects.create_user(email="g2@example.com", password="Senha12345!", role="manager")
    return Manager.objects.create(user=user, first_name="Outro", last_name="Gerente")


# ── Cadastro (somente admin root) ───────────────────────────────────────────

def test_admin_creates_manager(api, root_admin):
    r = api.post("/managers/", NEW, user=root_admin)
    assert r.status_code == 201, r.content
    body = r.json()
    assert body["first_name"] == "Nina" and body["user"]["email"] == NEW["email"]
    user = User.objects.get(email=NEW["email"])
    assert user.role == "manager" and user.is_active and user.is_trusty
    assert user.manager_profile.last_name == "Gestora"


def test_create_does_not_return_tokens_or_password(api, root_admin):
    r = api.post("/managers/", NEW, user=root_admin)
    assert "password" not in r.content.decode() and "access" not in r.json()


def test_create_sends_welcome_email_with_valid_temp_password(api, root_admin, celery_delay, django_capture_on_commit_callbacks):
    with django_capture_on_commit_callbacks(execute=True):
        assert api.post("/managers/", NEW, user=root_admin).status_code == 201
    celery_delay.assert_called_once()
    user_id, temp_password = celery_delay.call_args.args
    assert User.objects.get(pk=user_id).check_password(temp_password)


def test_create_only_email_is_enough(api, root_admin):
    r = api.post("/managers/", {"email": "so.email@example.com"}, user=root_admin)
    assert r.status_code == 201 and r.json()["first_name"] in (None, "")


def test_create_duplicate_email_is_409(api, root_admin, manager_user):
    assert api.post("/managers/", {"email": manager_user.email}, user=root_admin).status_code == 409
    assert User.objects.filter(email=manager_user.email).count() == 1


def test_create_invalid_email_is_422(api, root_admin):
    assert api.post("/managers/", {"email": "nao-e-email"}, user=root_admin).status_code == 422


@pytest.mark.parametrize("who", ["manager_user", "verified_employee", "verified_client"])
def test_only_root_admin_can_create(api, request, who):
    r = api.post("/managers/", NEW, user=request.getfixturevalue(who))
    assert r.status_code == 403
    assert not User.objects.filter(email=NEW["email"]).exists()


def test_create_requires_authentication(api):
    assert api.post("/managers/", NEW).status_code == 401


# ── Leitura ─────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("who", ["root_admin", "manager_user"])
def test_admin_and_manager_can_list(api, request, manager_user, other_manager, who):
    r = api.get("/managers/", user=request.getfixturevalue(who))
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 2 and len(body["items"]) == 2


def test_list_paginates(api, root_admin, manager_user, other_manager):
    body = api.get("/managers/", user=root_admin, page=1, page_size=1).json()
    assert len(body["items"]) == 1 and body["pages"] == 2


@pytest.mark.parametrize("who", ["verified_employee", "verified_client"])
def test_employee_and_client_cannot_list_or_read(api, request, manager_user, who):
    user = request.getfixturevalue(who)
    assert api.get("/managers/", user=user).status_code == 403
    assert api.get(f"/managers/{manager_user.manager_profile.id}", user=user).status_code == 403


def test_get_detail(api, root_admin, manager_user):
    r = api.get(f"/managers/{manager_user.manager_profile.id}", user=root_admin)
    assert r.status_code == 200 and r.json()["user"]["email"] == manager_user.email


def test_get_unknown_is_404(api, root_admin):
    assert api.get(f"/managers/{uuid.uuid4()}", user=root_admin).status_code == 404


# ── Atualização ─────────────────────────────────────────────────────────────

def test_manager_updates_own_profile(api, manager_user):
    r = api.patch(f"/managers/{manager_user.manager_profile.id}", {"first_name": "Renata"}, user=manager_user)
    assert r.status_code == 200 and r.json()["first_name"] == "Renata"
    manager_user.manager_profile.refresh_from_db()
    assert manager_user.manager_profile.first_name == "Renata"
    assert manager_user.manager_profile.last_name == "Gerente"  # campo não enviado fica intacto


def test_admin_updates_manager(api, root_admin, other_manager):
    r = api.patch(f"/managers/{other_manager.id}", {"last_name": "Silva"}, user=root_admin)
    assert r.status_code == 200 and r.json()["last_name"] == "Silva"


def test_update_unknown_is_404(api, root_admin):
    assert api.patch(f"/managers/{uuid.uuid4()}", {"first_name": "X"}, user=root_admin).status_code == 404


def test_client_cannot_update(api, verified_client, manager_user):
    assert api.patch(f"/managers/{manager_user.manager_profile.id}", {"first_name": "X"}, user=verified_client).status_code == 403


# ── Foto ────────────────────────────────────────────────────────────────────

def test_upload_and_remove_photo(api, manager_user):
    mid = manager_user.manager_profile.id
    r = api.post_form(f"/managers/{mid}/photo", {"photo": image_file()}, user=manager_user)
    assert r.status_code == 200, r.content
    manager_user.manager_profile.refresh_from_db()
    assert manager_user.manager_profile.photo.name != DEFAULT_MANAGER_PHOTO

    r = api.delete(f"/managers/{mid}/photo", user=manager_user)
    assert r.status_code == 200
    manager_user.manager_profile.refresh_from_db()
    assert manager_user.manager_profile.photo.name == DEFAULT_MANAGER_PHOTO


def test_replacing_photo_discards_old_file_but_never_the_default(api, manager_user, celery_delay):
    mid = manager_user.manager_profile.id
    api.post_form(f"/managers/{mid}/photo", {"photo": image_file("a.png")}, user=manager_user)
    celery_delay.assert_not_called()  # a anterior era a padrão: nunca apagar
    first = manager_user.manager_profile.__class__.objects.get(id=mid).photo.name

    api.post_form(f"/managers/{mid}/photo", {"photo": image_file("b.png")}, user=manager_user)
    celery_delay.assert_called_once_with(first)


def test_upload_rejects_invalid_extension(api, manager_user):
    bad = SimpleUploadedFile("doc.txt", b"nao sou imagem", content_type="text/plain")
    r = api.post_form(f"/managers/{manager_user.manager_profile.id}/photo", {"photo": bad}, user=manager_user)
    assert r.status_code == 400


def test_upload_rejects_corrupted_image(api, manager_user):
    bad = SimpleUploadedFile("foto.png", b"corrompido", content_type="image/png")
    r = api.post_form(f"/managers/{manager_user.manager_profile.id}/photo", {"photo": bad}, user=manager_user)
    assert r.status_code == 400


def test_photo_of_unknown_manager_is_404(api, root_admin):
    assert api.post_form(f"/managers/{uuid.uuid4()}/photo", {"photo": image_file()}, user=root_admin).status_code == 404
    assert api.delete(f"/managers/{uuid.uuid4()}/photo", user=root_admin).status_code == 404


# ── Exclusão ────────────────────────────────────────────────────────────────

def test_admin_deletes_manager_and_user(api, root_admin, other_manager):
    uid = other_manager.user_id
    assert api.delete(f"/managers/{other_manager.id}", user=root_admin).status_code == 204
    assert not Manager.objects.filter(id=other_manager.id).exists()
    assert not User.objects.filter(id=uid).exists()


def test_delete_unknown_is_404(api, root_admin):
    assert api.delete(f"/managers/{uuid.uuid4()}", user=root_admin).status_code == 404


def test_employee_cannot_delete(api, verified_employee, other_manager):
    assert api.delete(f"/managers/{other_manager.id}", user=verified_employee).status_code == 403
    assert Manager.objects.filter(id=other_manager.id).exists()


# ── /auth/me ────────────────────────────────────────────────────────────────

def test_me_exposes_manager_profile(api, manager_user):
    body = api.get("/auth/me", user=manager_user).json()
    assert body["user"]["role"] == "manager" and body["client"] is None and body["employee"] is None
    assert body["manager"]["id"] == str(manager_user.manager_profile.id)
    assert body["manager"]["first_name"] == "Gabi"