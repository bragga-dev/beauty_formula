"""
Versões vigentes dos documentos legais.

Ao alterar o TEXTO de um documento de forma relevante:
  1. edite o .md em apps/legal/documents/;
  2. incremente a versão e a data de vigência aqui.
Usuários com versão aceita diferente da vigente passam a ver
`consent.needs_acceptance = true` em GET /auth/me e precisam aceitar de novo.
"""

TERMS_VERSION = "1.0"
TERMS_EFFECTIVE_DATE = "2026-11-12"

PRIVACY_VERSION = "1.0"
PRIVACY_EFFECTIVE_DATE = "2026-11-12"

DOC_TERMS = "terms"
DOC_PRIVACY = "privacy"
DOC_MARKETING = "marketing"