"""Toda tarefa do beat precisa estar registrada no worker (senão o Celery recusa a execução)."""
import pytest

from beauty_formula.config.celery import app


@pytest.fixture(scope="module")
def registered():
    app.loader.import_default_modules()
    return app.tasks


@pytest.mark.parametrize("key", sorted(app.conf.beat_schedule))
def test_beat_task_is_registered(registered, key):
    name = app.conf.beat_schedule[key]["task"]
    assert name in registered, f"{key}: tarefa '{name}' não registrada (importe no tasks/__init__.py ou corrija o nome)"


@pytest.mark.parametrize("name", [
    "send_verification_email_manager", "complete_overdue_scheduling", "sending_reminder",
    "purge_expired_contacts_task", "purge_unverified_accounts_task",
])
def test_tasks_dispatched_by_the_app_are_registered(registered, name):
    assert any(t.endswith(name) for t in registered), name