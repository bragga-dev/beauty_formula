from ninja import Schema


class LegalDocumentOut(Schema):
    document: str         
    title: str
    version: str
    effective_date: str   
    content: str          


class LegalVersionsOut(Schema):
    terms_version: str
    terms_effective_date: str
    privacy_version: str
    privacy_effective_date: str


__all__ = ["LegalDocumentOut", "LegalVersionsOut"]