"""Retenção dos contatos do site (LGPD) + agendamento das rotinas no Celery beat."""
from datetime import timedelta

import pytest
from django.utils import timezone

from beauty_formula.apps.website.models.contact_models import Contact
from beauty_formula.apps.website.services.contact_service import purge_expired_contacts
from beauty_formula.apps.website.tasks.purge_expired_contacts import purge_expired_contacts_task

pytestmark = pytest.mark.django_db

S = Contact.ContactStatus


def _contact(n, status, age_days):
    c = Contact.objects.create(full_name=f"Pessoa {n}", subject="question", message="oi",
                               email=f"p{n}@example.com", phone="77999990000", status=status)
    Contact.objects.filter(pk=c.pk).update(created_at=timezone.now() - timedelta(days=age_days))
    return c


def test_only_old_handled_contacts_are_deleted(settings):
    settings.LEGAL_CONTACT_RETENTION_MONTHS = 12
    old_resolved = _contact(1, S.RESOLVED, 400)
    old_archived = _contact(2, S.ARCHIVED, 500)
    old_pending = _contact(3, S.PENDING, 800)
    old_in_progress = _contact(4, S.IN_PROGRESS, 800)
    recent_resolved = _contact(5, S.RESOLVED, 30)

    assert purge_expired_contacts() == 2
    assert set(Contact.objects.values_list("pk", flat=True)) == {old_pending.pk, old_in_progress.pk, recent_resolved.pk}
    assert not Contact.objects.filter(pk__in=[old_resolved.pk, old_archived.pk]).exists()


def test_window_comes_from_settings(settings):
    c = _contact(1, S.RESOLVED, 100)
    settings.LEGAL_CONTACT_RETENTION_MONTHS = 6
    assert purge_expired_contacts() == 0
    settings.LEGAL_CONTACT_RETENTION_MONTHS = 3
    assert purge_expired_contacts() == 1
    assert not Contact.objects.filter(pk=c.pk).exists()


def test_task_returns_count(settings):
    settings.LEGAL_CONTACT_RETENTION_MONTHS = 1
    _contact(1, S.RESOLVED, 90)
    assert purge_expired_contacts_task() == 1