"""
Matriz de permissões da API.

1. Toda rota que NÃO é pública exige autenticação (anônimo -> 401).
2. O conjunto de rotas públicas é fixo: se alguém esquecer o `auth=` num
   endpoint novo, este teste quebra em vez de a rota ir pro ar aberta.
3. Cada role recebe 403 nas rotas que não são dela.
"""
import uuid

import pytest

from beauty_formula.config.api import api as ninja_api

# Rotas que PODEM ser acessadas sem token (método, path openapi).
PUBLIC_ROUTES = {
    ("post", "/api/auth/login"),
    ("post", "/api/auth/google"),
    ("post", "/api/auth/password-reset/request"),
    ("post", "/api/auth/password-reset/confirm"),
    ("post", "/api/auth/refresh"),
    ("post", "/api/auth/register"),
    ("get", "/api/auth/verify-email/{uidb64}/{token}"),
    ("post", "/api/auth/resend-verification"),
    ("get", "/api/employees/team"),
    ("get", "/api/employees/team/{employee_id}"),
    ("get", "/api/services/list-services"),
    ("get", "/api/services/detail-service/{service_id}"),
    ("get", "/api/availability/eligible-employees/{service_id}"),
    ("get", "/api/availability/employee/{employee_id}"),
    ("get", "/api/availability/employee/{employee_id}/public-calendar"),
    ("get", "/api/average-ratings/all"),
    ("get", "/api/average-ratings/service/{service_id}"),
    ("get", "/api/average-ratings/service/{service_id}/summary"),
    ("get", "/api/average-ratings/employee/{employee_id}"),
    ("get", "/api/average-ratings/employee/{employee_id}/summary"),
    ("get", "/api/products/list-public-products"),
    ("get", "/api/products/detail-product/{product_id}"),
    ("post", "/api/contacts/create-contact"),
    ("post", "/api/payments/webhook"),
}

_METHODS = {"get", "post", "put", "patch", "delete"}


def _operations():
    schema = ninja_api.get_openapi_schema()
    for path, item in schema["paths"].items():
        for method, op in item.items():
            if method in _METHODS:
                yield method, path, op


def _concrete(path: str) -> str:
    out = path
    for name in set(__import__("re").findall(r"{(\w+)}", path)):
        value = "1" if name == "session_id" else ("x" if name in {"uidb64", "token", "block_type"} else str(uuid.uuid4()))
        out = out.replace("{" + name + "}", value)
    return out


def _call(client, method, path):
    kwargs = {"content_type": "application/json"} if method != "get" else {}
    return getattr(client, method)(_concrete(path), **kwargs)


def test_openapi_lists_routes():
    assert len(list(_operations())) > 100


def test_public_routes_are_exactly_the_expected_ones():
    actual_public = {(m, p) for m, p, op in _operations() if not op.get("security")}
    unexpected = actual_public - PUBLIC_ROUTES
    missing = PUBLIC_ROUTES - actual_public
    assert not unexpected, f"Rotas públicas NÃO previstas (faltou auth=?): {sorted(unexpected)}"
    assert not missing, f"Rotas que deveriam ser públicas e agora exigem auth: {sorted(missing)}"


@pytest.mark.django_db
@pytest.mark.parametrize(
    "method,path",
    sorted((m, p) for m, p, op in _operations() if op.get("security")),
)
def test_protected_route_rejects_anonymous(client, method, path):
    response = _call(client, method, path)
    assert response.status_code == 401, f"{method.upper()} {path} -> {response.status_code}"


# ── Role x rota (amostra representativa de cada área) ────────────────────────

ADMIN_OR_MANAGER_ONLY = [
    ("get", "/admin/list-users"),
    ("get", "/scheduling/list-all"),
    ("get", "/payments/list-all"),
    ("get", "/commissions/list-all"),
    ("get", "/reports/monthly-balance"),
    ("get", "/contacts/list-contacts"),
    ("get", "/services/list-private-services"),
    ("get", "/products/list-private-products"),
    ("get", "/notifications/admin/list-all"),
    ("get", "/managers/"),
]


@pytest.mark.django_db
@pytest.mark.parametrize("method,path", ADMIN_OR_MANAGER_ONLY)
@pytest.mark.parametrize("who", ["verified_client", "verified_employee"])
def test_admin_or_manager_routes_forbid_client_and_employee(api, request, who, method, path):
    user = request.getfixturevalue(who)
    assert getattr(api, method)(path, user=user).status_code == 403


@pytest.mark.django_db
@pytest.mark.parametrize("method,path", ADMIN_OR_MANAGER_ONLY)
@pytest.mark.parametrize("who", ["root_admin", "manager_user"])
def test_admin_or_manager_routes_allow_admin_and_manager(api, request, who, method, path):
    user = request.getfixturevalue(who)
    assert getattr(api, method)(path, user=user).status_code == 200


CLIENT_ONLY = [
    ("get", "/scheduling/list-my-schedulings"),
    ("get", "/payments/my-payments"),
    ("get", "/average-ratings/my-ratings"),
]
EMPLOYEE_ONLY = [
    ("get", "/scheduling/list-employee-schedulings"),
    ("get", "/employee-services/list-my-services"),
    ("get", "/employee-working-hours/list-my-working-hours"),
    ("get", "/commissions/my-commissions/summary"),
]


@pytest.mark.django_db
@pytest.mark.parametrize("method,path", CLIENT_ONLY)
@pytest.mark.parametrize("who", ["verified_employee", "manager_user"])
def test_client_only_routes_forbid_others(api, request, who, method, path):
    assert getattr(api, method)(path, user=request.getfixturevalue(who)).status_code == 403


@pytest.mark.django_db
@pytest.mark.parametrize("method,path", EMPLOYEE_ONLY)
@pytest.mark.parametrize("who", ["verified_client", "manager_user"])
def test_employee_only_routes_forbid_others(api, request, who, method, path):
    assert getattr(api, method)(path, user=request.getfixturevalue(who)).status_code == 403


@pytest.mark.django_db
def test_unverified_user_is_blocked_everywhere(api, unverified_client_user):
    # token válido, mas e-mail não verificado
    assert api.get("/scheduling/list-my-schedulings", user=unverified_client_user).status_code in (401, 403)
    assert api.get("/auth/me", user=unverified_client_user).status_code in (401, 403)


@pytest.mark.django_db
def test_only_root_admin_can_create_manager(api, manager_user, root_admin):
    payload = {"email": "novo.gerente@example.com", "first_name": "Novo", "last_name": "Gerente"}
    assert api.post("/managers/", payload, user=manager_user).status_code == 403
    assert api.post("/managers/", payload, user=root_admin).status_code == 201