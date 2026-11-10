"""Fluxos de autenticação: cadastro, verificação, login, refresh, logout, senha."""
import pytest
from django.contrib.auth.tokens import default_token_generator
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from ninja_jwt.token_blacklist.models import BlacklistedToken, OutstandingToken
from ninja_jwt.tokens import RefreshToken

from beauty_formula.apps.accounts.models import User
from beauty_formula.apps.core.tokens.cookies import REFRESH_COOKIE_NAME
from beauty_formula.apps.core.tokens.signing import generate_uid_token

pytestmark = pytest.mark.django_db

STRONG = "Senha-Forte-98765!"


def _login(api, email, password):
    return api.post("/auth/login", {"email": email, "password": password})


# ── Cadastro / verificação ──────────────────────────────────────────────────

def test_register_creates_inactive_client_and_sets_refresh_cookie(api):
    r = api.post("/auth/register", {"email": "nova@example.com", "password": STRONG, "password2": STRONG})
    assert r.status_code == 201
    assert REFRESH_COOKIE_NAME in r.cookies
    assert r.cookies[REFRESH_COOKIE_NAME]["httponly"]
    user = User.objects.get(email="nova@example.com")
    assert user.role == "client" and user.is_active is False and user.is_trusty is False


def test_register_duplicate_email_is_409(api, verified_client):
    r = api.post("/auth/register", {"email": verified_client.email, "password": STRONG, "password2": STRONG})
    assert r.status_code == 409


@pytest.mark.parametrize("pwd", ["12345678", "password", "abcdefgh"])
def test_register_rejects_weak_password(api, pwd):
    r = api.post("/auth/register", {"email": "fraca@example.com", "password": pwd, "password2": pwd})
    assert r.status_code == 422


def test_register_password_mismatch(api):
    r = api.post("/auth/register", {"email": "x@example.com", "password": STRONG, "password2": STRONG + "x"})
    assert r.status_code == 422


def test_register_cannot_choose_role(api):
    r = api.post("/auth/register", {"email": "esperto@example.com", "password": STRONG, "password2": STRONG, "role": "admin"})
    assert r.status_code == 201
    assert User.objects.get(email="esperto@example.com").role == "client"


def test_verify_email_activates_user(api, unverified_client_user):
    uid, token = generate_uid_token(unverified_client_user)
    r = api.get(f"/auth/verify-email/{uid}/{token}")
    assert r.status_code in (200, 302)
    unverified_client_user.refresh_from_db()
    assert unverified_client_user.is_active and unverified_client_user.is_trusty


def test_verify_email_rejects_bad_token(api, unverified_client_user):
    uid, _ = generate_uid_token(unverified_client_user)
    r = api.get(f"/auth/verify-email/{uid}/token-invalido")
    assert r.status_code == 302 and "status=error" in r["Location"]
    unverified_client_user.refresh_from_db()
    assert unverified_client_user.is_active is False


def test_verify_email_redirect_url_encodes_the_email(api, db):
    from beauty_formula.apps.accounts.models.client import Client
    user = User.objects.create_user(email="ana+teste@example.com", password="Senha12345!", role="client")
    Client.objects.create(user=user, first_name="Ana", last_name="T")
    uid, token = generate_uid_token(user)
    location = api.get(f"/auth/verify-email/{uid}/{token}")["Location"]
    assert "email=ana%2Bteste%40example.com" in location


# ── Login ───────────────────────────────────────────────────────────────────

def test_login_ok_returns_access_and_cookie_but_not_refresh_in_body(api, verified_client):
    r = _login(api, verified_client.email, "Senha12345!")
    assert r.status_code == 200
    assert "access" in r.json() and "refresh" not in r.json()
    assert REFRESH_COOKIE_NAME in r.cookies


def test_login_wrong_password_is_401_and_generic(api, verified_client):
    r = _login(api, verified_client.email, "errada")
    assert r.status_code == 401
    r2 = _login(api, "naoexiste@example.com", "errada")
    assert r2.status_code == 401
    assert r.json() == r2.json()  # não vaza se o e-mail existe


def test_login_unverified_account_is_403(api, unverified_client_user):
    assert _login(api, unverified_client_user.email, "Senha12345!").status_code == 403


def test_login_is_rate_limited_per_email(api, verified_client):
    codes = [_login(api, verified_client.email, "errada").status_code for _ in range(7)]
    assert 429 in codes


def test_login_deactivated_user_cannot_login(api, verified_client):
    verified_client.is_active = False
    verified_client.save()
    assert _login(api, verified_client.email, "Senha12345!").status_code in (401, 403)


# ── Refresh / rotação ───────────────────────────────────────────────────────

def _login_cookie(api, user, password="Senha12345!"):
    r = _login(api, user.email, password)
    assert r.status_code == 200
    return r.cookies[REFRESH_COOKIE_NAME].value


def _refresh(api, cookie):
    api._c.cookies[REFRESH_COOKIE_NAME] = cookie
    return api.post("/auth/refresh")


def test_refresh_without_cookie_is_401(api):
    assert api.post("/auth/refresh").status_code == 401


def test_refresh_rotates_and_old_token_is_rejected(api, verified_client):
    old = _login_cookie(api, verified_client)
    r = _refresh(api, old)
    assert r.status_code == 200
    new = r.cookies[REFRESH_COOKIE_NAME].value
    assert new != old
    assert _refresh(api, old).status_code == 401  # reuso do antigo


def test_rotated_refresh_token_is_tracked_as_outstanding(api, verified_client):
    """O token novo precisa existir em OutstandingToken, senão logout-all/troca de senha não o revogam."""
    old = _login_cookie(api, verified_client)
    new = _refresh(api, old).cookies[REFRESH_COOKIE_NAME].value
    new_jti = RefreshToken(new)["jti"]
    assert OutstandingToken.objects.filter(jti=new_jti).exists()


def test_logout_all_revokes_rotated_refresh_token(api, verified_client):
    old = _login_cookie(api, verified_client)
    new = _refresh(api, old).cookies[REFRESH_COOKIE_NAME].value
    assert api.post("/auth/logout-all", user=verified_client).status_code == 200
    assert _refresh(api, new).status_code == 401


def test_change_password_revokes_rotated_refresh_token(api, verified_client):
    old = _login_cookie(api, verified_client)
    new = _refresh(api, old).cookies[REFRESH_COOKIE_NAME].value
    r = api.post("/auth/change-password", {
        "old_password": "Senha12345!", "new_password": STRONG, "new_password2": STRONG,
    }, user=verified_client)
    assert r.status_code == 200
    assert _refresh(api, new).status_code == 401


def test_refresh_of_deactivated_user_is_rejected(api, verified_client):
    cookie = _login_cookie(api, verified_client)
    verified_client.is_active = False
    verified_client.save()
    assert _refresh(api, cookie).status_code == 401


def test_logout_blacklists_refresh(api, verified_client):
    cookie = _login_cookie(api, verified_client)
    api._c.cookies[REFRESH_COOKIE_NAME] = cookie
    assert api.post("/auth/logout", user=verified_client).status_code == 200
    assert _refresh(api, cookie).status_code == 401


# ── Senha ───────────────────────────────────────────────────────────────────

def test_change_password_wrong_old_password(api, verified_client):
    r = api.post("/auth/change-password", {
        "old_password": "errada", "new_password": STRONG, "new_password2": STRONG,
    }, user=verified_client)
    assert r.status_code in (400, 401, 403)


def test_password_reset_request_does_not_enumerate(api, verified_client):
    a = api.post("/auth/password-reset/request", {"email": verified_client.email})
    b = api.post("/auth/password-reset/request", {"email": "ninguem@example.com"})
    assert a.status_code == b.status_code == 200
    assert a.json() == b.json()


def _reset_payload(user, password):
    uid = urlsafe_base64_encode(force_bytes(user.pk)).rstrip("=")
    return {"uid": uid, "token": default_token_generator.make_token(user), "new_password": password, "new_password2": password}


def test_password_reset_confirm_changes_password(api, verified_client):
    assert api.post("/auth/password-reset/confirm", _reset_payload(verified_client, STRONG)).status_code == 200
    verified_client.refresh_from_db()
    assert verified_client.check_password(STRONG)


def test_password_reset_token_is_single_use(api, verified_client):
    payload = _reset_payload(verified_client, STRONG)
    assert api.post("/auth/password-reset/confirm", payload).status_code == 200
    assert api.post("/auth/password-reset/confirm", payload).status_code == 400


@pytest.mark.parametrize("pwd", ["12345678", "password"])
def test_password_reset_rejects_weak_password(api, verified_client, pwd):
    r = api.post("/auth/password-reset/confirm", _reset_payload(verified_client, pwd))
    assert r.status_code == 422
    verified_client.refresh_from_db()
    assert not verified_client.check_password(pwd)


def test_password_reset_revokes_existing_sessions(api, verified_client):
    cookie = _login_cookie(api, verified_client)
    assert api.post("/auth/password-reset/confirm", _reset_payload(verified_client, STRONG)).status_code == 200
    assert _refresh(api, cookie).status_code == 401


# ── /me ─────────────────────────────────────────────────────────────────────

def test_me_returns_profile_by_role(api, verified_client, verified_employee):
    assert api.get("/auth/me", user=verified_client).status_code == 200
    assert api.get("/auth/me", user=verified_employee).status_code == 200