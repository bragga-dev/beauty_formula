"""Retenção de contas nunca verificadas (LGPD)."""
from datetime import timedelta

import pytest
from django.utils import timezone

from beauty_formula.apps.accounts.models import User
from beauty_formula.apps.accounts.models.client import Client
from beauty_formula.apps.accounts.services.account_retention_service import purge_unverified_accounts
from beauty_formula.apps.accounts.tasks.purge_unverified_accounts import purge_unverified_accounts_task

pytestmark = pytest.mark.django_db


def _client(email, *, age_days, verified=False, role="client"):
    user = User.objects.create_user(email=email, password="Senha12345!", role=role)
    if role == "client":
        Client.objects.get_or_create(user=user)
    User.objects.filter(pk=user.pk).update(
        is_trusty=verified, created_at=timezone.now() - timedelta(days=age_days),
    )
    return user


def test_old_unverified_client_is_deleted_with_its_profile(settings):
    settings.LEGAL_UNVERIFIED_ACCOUNT_RETENTION_DAYS = 30
    old = _client("velha@example.com", age_days=31)
    assert purge_unverified_accounts() == 1
    assert not User.objects.filter(pk=old.pk).exists()
    assert not Client.objects.filter(user_id=old.pk).exists()


def test_recent_verified_and_non_client_accounts_are_kept(settings):
    settings.LEGAL_UNVERIFIED_ACCOUNT_RETENTION_DAYS = 30
    keep = [
        _client("recente@example.com", age_days=5),
        _client("verificada@example.com", age_days=400, verified=True),
        _client("func@example.com", age_days=400, role="employee"),
    ]
    assert purge_unverified_accounts() == 0
    assert User.objects.filter(pk__in=[u.pk for u in keep]).count() == 3


def test_retention_window_comes_from_settings(settings):
    user = _client("janela@example.com", age_days=10)
    settings.LEGAL_UNVERIFIED_ACCOUNT_RETENTION_DAYS = 30
    assert purge_unverified_accounts() == 0
    settings.LEGAL_UNVERIFIED_ACCOUNT_RETENTION_DAYS = 7
    assert purge_unverified_accounts() == 1
    assert not User.objects.filter(pk=user.pk).exists()


def test_account_with_protected_records_is_kept(settings, employee, service):
    from beauty_formula.apps.services.models.scheduling import Scheduling
    from beauty_formula.apps.conftest import next_slot
    settings.LEGAL_UNVERIFIED_ACCOUNT_RETENTION_DAYS = 30
    user = _client("protegida@example.com", age_days=90)
    Scheduling.objects.create(
        service=service, client=user.client_profile, employee=employee,
        scheduled_time=next_slot(2), status=Scheduling.SchedulingStatus.CREATED,
    )
    assert purge_unverified_accounts() == 0
    assert User.objects.filter(pk=user.pk).exists()


def test_task_returns_count(settings):
    settings.LEGAL_UNVERIFIED_ACCOUNT_RETENTION_DAYS = 30
    _client("a@example.com", age_days=40)
    _client("b@example.com", age_days=40)
    assert purge_unverified_accounts_task() == 2