"""Documentos legais — públicos (precisam estar disponíveis antes do cadastro)."""
from django_ratelimit.decorators import ratelimit
from ninja import Router

from beauty_formula.apps.legal import constants
from beauty_formula.apps.legal.schemas.legal_schema import LegalDocumentOut, LegalVersionsOut
from beauty_formula.apps.legal.services.legal_service import get_current_versions, get_document

router = Router()


@router.get("/terms", response=LegalDocumentOut, auth=None, summary="Termos de Uso (versão vigente)")
@ratelimit(key="ip", rate="60/m", block=True)
def terms_router(request):
    return get_document(constants.DOC_TERMS)


@router.get("/privacy", response=LegalDocumentOut, auth=None, summary="Política de Privacidade (versão vigente)")
@ratelimit(key="ip", rate="60/m", block=True)
def privacy_router(request):
    return get_document(constants.DOC_PRIVACY)


@router.get("/versions", response=LegalVersionsOut, auth=None, summary="Versões vigentes dos documentos")
@ratelimit(key="ip", rate="60/m", block=True)
def versions_router(request):
    return get_current_versions()