"""
Repository de Contato — funções de persistência (criação, atualização de
status e exclusão) no banco de dados.

O model `Contact` não sobrescreve `save()` chamando `full_clean()` (ao
contrário de `Product`), então as funções aqui chamam `full_clean()`
explicitamente antes de salvar para converter erros de constraint (ex:
`unique_contact_name`) em `ValidationError` em vez de `IntegrityError` cru.
"""
from typing import Optional
from uuid import UUID

from django.db import transaction

from beauty_formula.apps.website.models.contact_models import Contact


UPDATABLE_CONTACT_FIELDS = {"status"}


@transaction.atomic
def create_contact(*, full_name: str, email: str, phone: str, message: str, subject: str = Contact.ContactSubject.OTHER) -> Contact:
    """Cria um novo contato (formulário público). Roda full_clean() antes de salvar."""
    contact = Contact(
        full_name=full_name,
        email=email,
        phone=phone,
        message=message,
        subject=subject,
    )
    contact.full_clean()
    contact.save()
    return contact


@transaction.atomic
def update_contact(contact: Contact, **fields) -> Contact:
    """
    Atualiza parcialmente um contato.

    Só o `status` é atualizável — os demais campos vêm do formulário
    público e não devem ser alterados pelo admin, apenas consultados.
    """
    unknown = set(fields) - UPDATABLE_CONTACT_FIELDS
    if unknown:
        raise ValueError(f"Campos não atualizáveis em Contact: {', '.join(sorted(unknown))}")

    if not fields:
        return contact  # nada a fazer

    for field, value in fields.items():
        setattr(contact, field, value)

    contact.full_clean()
    contact.save()
    return contact


@transaction.atomic
def delete_contact(contact: Contact) -> None:
    """
    Exclui um contato permanentemente do banco.
    Diferente de Product/Service, Contact não tem soft delete — não há
    agendamento nem FK dependendo dele, então a exclusão real é segura
    (e recomendável por retenção de dados/LGPD).
    """
    contact.delete()