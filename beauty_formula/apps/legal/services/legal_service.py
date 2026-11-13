"""
Documentos legais (Termos de Uso e Política de Privacidade).

Os textos ficam em apps/legal/documents/*.md com placeholders ($variavel) que
são preenchidos com os dados do Controlador (settings.LEGAL_*), para que a
troca de razão social/CNPJ/encarregado não exija editar o texto.
"""
from functools import lru_cache
from pathlib import Path
from string import Template

from django.conf import settings

from beauty_formula.apps.legal import constants
from beauty_formula.apps.legal.schemas.legal_schema import LegalDocumentOut, LegalVersionsOut

_DOCS_DIR = Path(__file__).resolve().parent.parent / "documents"

_DOCUMENTS = {
    constants.DOC_TERMS: {
        "title": "Termos de Uso",
        "file": "terms_of_use.md",
        "version": lambda: constants.TERMS_VERSION,
        "effective_date": lambda: constants.TERMS_EFFECTIVE_DATE,
    },
    constants.DOC_PRIVACY: {
        "title": "Política de Privacidade",
        "file": "privacy_policy.md",
        "version": lambda: constants.PRIVACY_VERSION,
        "effective_date": lambda: constants.PRIVACY_EFFECTIVE_DATE,
    },
}


@lru_cache(maxsize=None)
def _read(filename: str) -> str:
    return (_DOCS_DIR / filename).read_text(encoding="utf-8")


def _variables(version: str, effective_date: str) -> dict:
    return {
        "version": version,
        "effective_date": effective_date,
        "company_name": settings.LEGAL_COMPANY_NAME,
        "company_cnpj": settings.LEGAL_COMPANY_CNPJ,
        "company_address": settings.LEGAL_COMPANY_ADDRESS,
        "contact_email": settings.LEGAL_CONTACT_EMAIL,
        "dpo_name": settings.LEGAL_DPO_NAME,
        "dpo_email": settings.LEGAL_DPO_EMAIL,
        "contact_retention_months": settings.LEGAL_CONTACT_RETENTION_MONTHS,
        "unverified_days": settings.LEGAL_UNVERIFIED_ACCOUNT_RETENTION_DAYS,
    }


def get_document(kind: str) -> LegalDocumentOut:
    spec = _DOCUMENTS[kind]
    version = spec["version"]()
    effective_date = spec["effective_date"]()
    content = Template(_read(spec["file"])).safe_substitute(_variables(version, effective_date))
    return LegalDocumentOut(
        document=kind, title=spec["title"], version=version,
        effective_date=effective_date, content=content,
    )


def get_current_versions() -> LegalVersionsOut:
    return LegalVersionsOut(
        terms_version=constants.TERMS_VERSION,
        terms_effective_date=constants.TERMS_EFFECTIVE_DATE,
        privacy_version=constants.PRIVACY_VERSION,
        privacy_effective_date=constants.PRIVACY_EFFECTIVE_DATE,
    )