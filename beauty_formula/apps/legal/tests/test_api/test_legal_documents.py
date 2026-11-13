"""Termos de Uso e Política de Privacidade: públicos, versionados e com dados do Controlador."""
import pytest

from beauty_formula.apps.legal import constants

pytestmark = pytest.mark.django_db


@pytest.fixture
def controller(settings):
    settings.LEGAL_COMPANY_NAME = "Salão Teste LTDA"
    settings.LEGAL_COMPANY_CNPJ = "12.345.678/0001-90"
    settings.LEGAL_DPO_NAME = "Maria Encarregada"
    settings.LEGAL_DPO_EMAIL = "dpo@salaoteste.com.br"
    settings.LEGAL_CONTACT_RETENTION_MONTHS = 7
    settings.LEGAL_UNVERIFIED_ACCOUNT_RETENTION_DAYS = 11


@pytest.mark.parametrize("path, doc, title", [
    ("/legal/terms", "terms", "Termos de Uso"),
    ("/legal/privacy", "privacy", "Política de Privacidade"),
])
def test_documents_are_public(api, path, doc, title):
    r = api.get(path)
    assert r.status_code == 200
    body = r.json()
    assert body["document"] == doc and body["title"] == title and body["content"].startswith(f"# {title}")


def test_documents_carry_current_versions(api):
    terms = api.get("/legal/terms").json()
    privacy = api.get("/legal/privacy").json()
    assert (terms["version"], terms["effective_date"]) == (constants.TERMS_VERSION, constants.TERMS_EFFECTIVE_DATE)
    assert (privacy["version"], privacy["effective_date"]) == (constants.PRIVACY_VERSION, constants.PRIVACY_EFFECTIVE_DATE)
    assert f"Versão {terms['version']}" in terms["content"]


def test_versions_endpoint(api):
    assert api.get("/legal/versions").json() == {
        "terms_version": constants.TERMS_VERSION, "terms_effective_date": constants.TERMS_EFFECTIVE_DATE,
        "privacy_version": constants.PRIVACY_VERSION, "privacy_effective_date": constants.PRIVACY_EFFECTIVE_DATE,
    }


def test_controller_data_is_filled_in(api, controller):
    privacy = api.get("/legal/privacy").json()["content"]
    terms = api.get("/legal/terms").json()["content"]
    for text in (privacy, terms):
        assert "Salão Teste LTDA" in text and "12.345.678/0001-90" in text and "dpo@salaoteste.com.br" in text
    assert "Maria Encarregada" in privacy


def test_retention_values_come_from_settings(api, controller):
    privacy = api.get("/legal/privacy").json()["content"]
    assert "7 meses" in privacy and "11 dias" in privacy


@pytest.mark.parametrize("path", ["/legal/terms", "/legal/privacy"])
def test_no_unresolved_placeholders(api, controller, path):
    content = api.get(path).json()["content"]
    assert "$" not in content


def test_privacy_policy_covers_lgpd_essentials(api):
    content = api.get("/legal/privacy").json()["content"]
    for expected in ("Encarregado", "art. 18", "ANPD", "Base legal", "Transferência internacional", "Por quanto tempo"):
        assert expected.lower() in content.lower(), expected


def test_documents_endpoints_are_rate_limited(api):
    codes = [api.get("/legal/versions").status_code for _ in range(65)]
    assert 429 in codes