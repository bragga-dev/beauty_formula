"""
Queries de Contato — Funções para buscar e filtrar contatos.
"""
from typing import Optional
from uuid import UUID
from django.db.models import Q, QuerySet
from beauty_formula.apps.website.models.contact_models import Contact


# ═══════════════════════════════════════════════════════════════════════════════
# Listagem Geral
# ═══════════════════════════════════════════════════════════════════════════════

def get_all_contacts() -> QuerySet[Contact]:
    """Retorna todos os contatos, do mais recente pro mais antigo."""
    return Contact.objects.all().order_by("-created_at")


def get_contacts_by_status(status: str) -> QuerySet[Contact]:
    """Retorna contatos filtrados por status."""
    return Contact.objects.filter(status=status).order_by("-created_at")


# ═══════════════════════════════════════════════════════════════════════════════
# Buscas Básicas por ID
# ═══════════════════════════════════════════════════════════════════════════════

def get_contact_by_id(contact_id: UUID) -> Optional[Contact]:
    """Retorna o contato pelo ID, ou None se não existir."""
    return Contact.objects.filter(id=contact_id).first()


# ═══════════════════════════════════════════════════════════════════════════════
# Buscas por Nome/Email
# ═══════════════════════════════════════════════════════════════════════════════

def get_contact_by_name(full_name: str) -> Optional[Contact]:
    """Retorna contato pelo nome completo (case-insensitive)."""
    if not full_name:
        return None
    return Contact.objects.filter(full_name__iexact=full_name).first()


def search_contacts(query: str) -> QuerySet[Contact]:
    """Busca contatos por nome, e-mail ou mensagem."""
    if not query:
        return Contact.objects.none()
    return Contact.objects.filter(
        Q(full_name__icontains=query) | Q(email__icontains=query) | Q(message__icontains=query)
    )


# ═══════════════════════════════════════════════════════════════════════════════
# Filtros Avançados
# ═══════════════════════════════════════════════════════════════════════════════

def filter_contacts(
    search: Optional[str] = None,
    status: Optional[str] = None,
    subject: Optional[str] = None,
    order_by: str = "-created_at",
) -> QuerySet[Contact]:

    q = Q()

    if search:
        q &= Q(full_name__icontains=search) | Q(email__icontains=search) | Q(message__icontains=search)

    if status:
        q &= Q(status=status)

    if subject:
        q &= Q(subject=subject)

    qs = Contact.objects.filter(q) if q else Contact.objects.all()
    return qs.order_by(order_by)


# ═══════════════════════════════════════════════════════════════════════════════
# Utilitários
# ═══════════════════════════════════════════════════════════════════════════════

def validate_contact_exists(contact_id: UUID) -> bool:
    """Verifica se um contato existe."""
    return Contact.objects.filter(id=contact_id).exists()


def validate_contact_name_available(full_name: str) -> bool:
    """
    Verifica se o nome está disponível (respeitando a UniqueConstraint
    do model). Usado antes de criar, pra devolver um erro claro em vez
    de deixar estourar IntegrityError/ValidationError direto do banco.
    """
    return not Contact.objects.filter(full_name__iexact=full_name).exists()