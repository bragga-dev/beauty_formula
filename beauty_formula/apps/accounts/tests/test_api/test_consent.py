"""LGPD — consentimento: cadastro, Google, /me, novo aceite, revogação, histórico, export e exclusão."""
import json
from unittest.mock import patch

import pytest

from beauty_formula.apps.accounts.models import User
from beauty_formula.apps.accounts.models.consent_log import ConsentLog
from beauty_formula.apps.accounts.services import consent_service
from beauty_formula.apps.core.exceptions.auth import InvalidGoogleToken
from beauty_formula.apps.legal import constants

pytestmark = pytest.mark.django_db

STRONG = "Senha-Forte-98765!"
PASSWORD = "Senha12345!"
ACCEPT = {"accept_terms": True, "accept_privacy_policy": True}


def _register(api, email="lgpd@example.com", ip="203.0.113.7", **extra):
    payload = {"email": email, "password": STRONG, "password2": STRONG, **extra}
    return api._c.post("/api/auth/register", data=json.dumps(payload), content_type="application/json",
                       HTTP_X_REAL_IP=ip, HTTP_USER_AGENT="pytest-agent/1.0")


# ── Cadastro por e-mail ─────────────────────────────────────────────────────

@pytest.mark.parametrize("consent", [
    {}, {"accept_terms": True}, {"accept_privacy_policy": True},
    {"accept_terms": False, "accept_privacy_policy": True},
    {"accept_terms": True, "accept_privacy_policy": False},
])
def test_register_requires_both_acceptances(api, consent):
    assert _register(api, **consent).status_code == 422
    assert not User.objects.filter(email="lgpd@example.com").exists()


def test_register_records_consent_on_user_and_in_audit_log(api):
    assert _register(api, **ACCEPT).status_code == 201
    user = User.objects.get(email="lgpd@example.com")
    assert user.terms_version == constants.TERMS_VERSION and user.terms_accepted_at is not None
    assert user.privacy_version == constants.PRIVACY_VERSION and user.privacy_accepted_at is not None
    assert user.marketing_opt_in is False and user.marketing_opt_in_at is None

    logs = ConsentLog.objects.filter(user_ref=user.id)
    assert {(l.document, l.action, l.source) for l in logs} == {
        ("terms", "accepted", "signup"), ("privacy", "accepted", "signup"),
    }
    assert all(l.ip_address == "203.0.113.7" and l.user_agent == "pytest-agent/1.0" for l in logs)
    assert {l.version for l in logs} == {constants.TERMS_VERSION, constants.PRIVACY_VERSION}


def test_marketing_is_optional_and_off_by_default(api):
    _register(api, **ACCEPT)
    assert not ConsentLog.objects.filter(document="marketing").exists()


def test_register_with_marketing_opt_in_logs_it(api):
    _register(api, marketing_opt_in=True, **ACCEPT)
    user = User.objects.get(email="lgpd@example.com")
    assert user.marketing_opt_in is True and user.marketing_opt_in_at is not None
    assert ConsentLog.objects.filter(user_ref=user.id, document="marketing", action="accepted").count() == 1


# ── Cadastro via Google ─────────────────────────────────────────────────────

CLAIMS = {"email": "google.user@example.com", "email_verified": True, "given_name": "Gui", "family_name": "Lima"}


def _google(api, **extra):
    payload = {"id_token": "x" * 20, **extra}
    with patch("beauty_formula.apps.accounts.services.user_service.verify_google_id_token", return_value=CLAIMS):
        return api._c.post("/api/auth/google", data=json.dumps(payload), content_type="application/json",
                           HTTP_X_REAL_IP="198.51.100.9")


def test_google_signup_without_consent_is_rejected(api):
    assert _google(api).status_code == 400
    assert _google(api, accept_terms=True).status_code == 400
    assert not User.objects.filter(email=CLAIMS["email"]).exists()


def test_google_signup_with_consent_records_source_google(api):
    r = _google(api, marketing_opt_in=True, **ACCEPT)
    assert r.status_code == 201
    user = User.objects.get(email=CLAIMS["email"])
    assert user.terms_version == constants.TERMS_VERSION and user.marketing_opt_in is True
    assert set(ConsentLog.objects.filter(user_ref=user.id).values_list("source", flat=True)) == {"google"}
    assert ConsentLog.objects.filter(user_ref=user.id).count() == 3


def test_google_login_of_existing_account_does_not_require_consent(api):
    _google(api, **ACCEPT)
    before = ConsentLog.objects.count()
    assert _google(api).status_code == 200
    assert ConsentLog.objects.count() == before


def test_google_invalid_token_is_still_401(api):
    with patch("beauty_formula.apps.accounts.services.user_service.verify_google_id_token", side_effect=InvalidGoogleToken("x")):
        r = api._c.post("/api/auth/google", data=json.dumps({"id_token": "x" * 20, **ACCEPT}), content_type="application/json")
    assert r.status_code == 401


# ── /auth/me ────────────────────────────────────────────────────────────────

def test_me_shows_consent_up_to_date_after_signup(api, verified_client):
    consent_service.record_signup_consent(verified_client, marketing_opt_in=False, source="signup", ip=None, user_agent="")
    c = api.get("/auth/me", user=verified_client).json()["consent"]
    assert c["needs_acceptance"] is False
    assert c["terms_version_accepted"] == constants.TERMS_VERSION == c["current_terms_version"]


def test_account_created_by_admin_needs_acceptance(api, verified_employee):
    c = api.get("/auth/me", user=verified_employee).json()["consent"]
    assert c["needs_acceptance"] is True and c["terms_version_accepted"] == "" and c["terms_accepted_at"] is None


# ── Novo aceite ─────────────────────────────────────────────────────────────

def test_employee_accepts_current_documents(api, verified_employee):
    r = api.post("/auth/consents/accept", ACCEPT, user=verified_employee)
    assert r.status_code == 200 and r.json()["needs_acceptance"] is False
    verified_employee.refresh_from_db()
    assert verified_employee.terms_version == constants.TERMS_VERSION
    assert set(ConsentLog.objects.filter(user_ref=verified_employee.id).values_list("source", flat=True)) == {"re_accept"}


@pytest.mark.parametrize("bad", [
    {"accept_terms": True, "accept_privacy_policy": False},
    {"accept_terms": False, "accept_privacy_policy": True},
    {"accept_terms": False, "accept_privacy_policy": False},
])
def test_accept_requires_both(api, verified_employee, bad):
    assert api.post("/auth/consents/accept", bad, user=verified_employee).status_code == 400
    assert not ConsentLog.objects.filter(user_ref=verified_employee.id).exists()


def test_accept_can_opt_into_marketing(api, verified_employee):
    api.post("/auth/consents/accept", {**ACCEPT, "marketing_opt_in": True}, user=verified_employee)
    verified_employee.refresh_from_db()
    assert verified_employee.marketing_opt_in is True


def test_new_document_version_requires_new_acceptance(api, verified_client, monkeypatch):
    consent_service.record_signup_consent(verified_client, marketing_opt_in=False, source="signup", ip=None, user_agent="")
    assert api.get("/auth/me", user=verified_client).json()["consent"]["needs_acceptance"] is False

    monkeypatch.setattr(constants, "PRIVACY_VERSION", "2.0")
    assert api.get("/auth/me", user=verified_client).json()["consent"]["needs_acceptance"] is True

    assert api.post("/auth/consents/accept", ACCEPT, user=verified_client).status_code == 200
    verified_client.refresh_from_db()
    assert verified_client.privacy_version == "2.0"
    assert ConsentLog.objects.filter(user_ref=verified_client.id, document="privacy", version="2.0").exists()
    assert ConsentLog.objects.filter(user_ref=verified_client.id, document="privacy", version="1.0").exists()


# ── Revogação (comunicações promocionais) ───────────────────────────────────

def test_marketing_opt_in_and_revoke_are_logged(api, verified_client):
    assert api.patch("/auth/consents/marketing", {"opt_in": True}, user=verified_client).json()["marketing_opt_in"] is True
    assert api.patch("/auth/consents/marketing", {"opt_in": False}, user=verified_client).json()["marketing_opt_in"] is False
    verified_client.refresh_from_db()
    assert verified_client.marketing_opt_in is False and verified_client.marketing_opt_in_at is not None
    actions = list(ConsentLog.objects.filter(user_ref=verified_client.id, document="marketing").order_by("created_at").values_list("action", "source"))
    assert actions == [("accepted", "settings"), ("revoked", "settings")]


def test_marketing_same_value_is_idempotent(api, verified_client):
    api.patch("/auth/consents/marketing", {"opt_in": False}, user=verified_client)
    assert not ConsentLog.objects.filter(user_ref=verified_client.id).exists()
    api.patch("/auth/consents/marketing", {"opt_in": True}, user=verified_client)
    api.patch("/auth/consents/marketing", {"opt_in": True}, user=verified_client)
    assert ConsentLog.objects.filter(user_ref=verified_client.id).count() == 1


@pytest.mark.parametrize("method, path", [("get", "/auth/consents/history"), ("post", "/auth/consents/accept"), ("patch", "/auth/consents/marketing")])
def test_consent_routes_require_authentication(api, method, path):
    assert getattr(api, method)(path).status_code == 401


# ── Histórico / exportação ──────────────────────────────────────────────────

def test_history_is_mine_only_and_newest_first(api, verified_client, other_verified_client):
    api.patch("/auth/consents/marketing", {"opt_in": True}, user=verified_client)
    api.patch("/auth/consents/marketing", {"opt_in": False}, user=verified_client)
    api.patch("/auth/consents/marketing", {"opt_in": True}, user=other_verified_client)

    mine = api.get("/auth/consents/history", user=verified_client).json()
    assert [h["action"] for h in mine] == ["revoked", "accepted"]
    assert api.get("/auth/consents/history", user=other_verified_client).json().__len__() == 1


def test_export_includes_consents(api, verified_client):
    consent_service.record_signup_consent(verified_client, marketing_opt_in=True, source="signup", ip="192.0.2.1", user_agent="ua")
    body = json.loads(api.get("/auth/export-my-data", user=verified_client).content)
    c = body["consentimentos"]
    assert c["termos_de_uso"]["versao"] == constants.TERMS_VERSION
    assert c["politica_de_privacidade"]["versao"] == constants.PRIVACY_VERSION
    assert c["comunicacoes_promocionais"]["ativo"] is True
    assert len(c["historico"]) == 3 and c["historico"][0]["ip"] == "192.0.2.1"


# ── Exclusão / anonimização ─────────────────────────────────────────────────

def test_audit_log_survives_account_deletion_without_pointing_to_the_user(api, verified_client):
    uid = verified_client.id
    consent_service.record_signup_consent(verified_client, marketing_opt_in=False, source="signup", ip="192.0.2.5", user_agent="ua")
    r = api.delete("/auth/delete-account", user=verified_client, data={"password": PASSWORD})
    assert r.status_code in (200, 204), r.content
    assert not User.objects.filter(id=uid).exists()
    logs = ConsentLog.objects.filter(user_ref=uid)
    assert logs.count() == 2 and all(l.user_id is None for l in logs)


def test_anonymization_turns_marketing_off(api, verified_client, client_profile, make_scheduling):
    from beauty_formula.apps.services.models.scheduling import Scheduling
    from django.utils import timezone
    verified_client.marketing_opt_in = True
    verified_client.save(update_fields=["marketing_opt_in"])
    make_scheduling(status=Scheduling.SchedulingStatus.COMPLETED, days_ahead=-1, completed_at=timezone.now())

    r = api.delete("/auth/delete-account", user=verified_client, data={"password": PASSWORD})
    assert r.status_code in (200, 204), r.content
    verified_client.refresh_from_db()
    assert verified_client.marketing_opt_in is False and verified_client.is_active is False
    assert verified_client.email.endswith("@anonimizado.invalid")