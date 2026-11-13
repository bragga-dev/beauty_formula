import uuid
from typing import Optional

from django.conf import settings
from django.db.models import QuerySet
from django.utils import timezone
from dateutil.relativedelta import relativedelta

from beauty_formula.apps.website.models.contact_models import Contact
from beauty_formula.apps.website.repositories.contact_repository import (
    create_contact,
    update_contact,
    delete_contact,
    delete_contacts_older_than,
)
from beauty_formula.apps.website.schemas.contact_schema import (
    ContactCreateIn,
    ContactUpdateIn,
    ContactOut,
)
from beauty_formula.apps.website.selectors.contact_selector import (
    get_contact_by_id,
    filter_contacts,
    validate_contact_name_available,
)

from beauty_formula.apps.core.exceptions.contact_exception import (
    ContactNotFound,
    ContactNameAlreadyExists,
)
from beauty_formula.apps.legal import constants
from beauty_formula.apps.website.tasks.send_email_confirm_contact import send_email_confirm_contact
from beauty_formula.apps.website.tasks.send_email_notify_admins import send_email_notify_admins


def create_contact_public(data: ContactCreateIn) -> ContactOut:
    """
    Cria um contato a partir do formulário público do site.
    """
    if not validate_contact_name_available(data.full_name):
        raise ContactNameAlreadyExists()

    contact = create_contact(
        full_name=data.full_name,
        email=data.email,
        phone=data.phone,
        message=data.message,
        subject=data.subject,
        privacy_policy_version=constants.PRIVACY_VERSION,
        consent_given_at=timezone.now(),
    )
    send_email_confirm_contact.delay(
        full_name=data.full_name,
        email=data.email,
        subject=data.subject,
        message=data.message,
        created_at=contact.created_at,
        phone=data.phone,
    )
    send_email_notify_admins.delay(
        full_name=data.full_name,
        email=data.email,
        subject=data.subject,
        message=data.message,
        created_at=contact.created_at,
        phone=data.phone,
    )
    return ContactOut.from_orm(contact)


def list_all_contacts_for_admin(
    search: Optional[str] = None,
    status: Optional[str] = None,
    subject: Optional[str] = None,
) -> QuerySet[Contact]:
    """Lista contatos com filtros opcionais, apenas Admins podem acessar esse recurso."""
    return filter_contacts(search=search, status=status, subject=subject)


def detail_contact_for_admin(contact_id: uuid.UUID) -> Contact:
    """Exibe detalhes de um contato, apenas Admins podem acessar esse recurso."""
    contact = get_contact_by_id(contact_id=contact_id)
    if contact is None:
        raise ContactNotFound()
    return contact


def update_contact_status_for_admin(contact_id: uuid.UUID, payload: ContactUpdateIn) -> ContactOut:
    """Atualiza o status de um contato (pending/in_progress/resolved/archived)."""
    contact = get_contact_by_id(contact_id=contact_id)
    if contact is None:
        raise ContactNotFound()

    fields = payload.model_dump(exclude_unset=True)
    updated = update_contact(contact=contact, **fields)
    return ContactOut.from_orm(updated)


def delete_contact_for_admin(contact_id: uuid.UUID) -> None:
    """Exclui um contato permanentemente, apenas Admins podem fazer essa ação."""
    contact = get_contact_by_id(contact_id=contact_id)
    if contact is None:
        raise ContactNotFound()
    delete_contact(contact=contact)


def purge_expired_contacts() -> int:
    """
    Retenção (LGPD — princípio da necessidade): exclui contatos RESOLVIDOS ou
    ARQUIVADOS mais antigos que settings.LEGAL_CONTACT_RETENTION_MONTHS.
    Contatos pendentes/em andamento nunca são apagados por esta rotina.
    """
    cutoff = timezone.now() - relativedelta(months=settings.LEGAL_CONTACT_RETENTION_MONTHS)
    return delete_contacts_older_than(
        cutoff=cutoff,
        statuses=[Contact.ContactStatus.RESOLVED, Contact.ContactStatus.ARCHIVED],
    )