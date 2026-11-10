"""Tasks periódicas do módulo de serviços (fan-out, auto-conclusão, expiração de bloqueio)."""
from datetime import timedelta

import pytest
from django.utils import timezone

from beauty_formula.apps.services.models.employee_time_off import EmployeeTimeOff
from beauty_formula.apps.services.models.scheduling import Scheduling
from beauty_formula.apps.services.tasks.close_overdue_schedulings import close_overdue_schedulings
from beauty_formula.apps.services.tasks.complete_overdue_scheduling import complete_overdue_scheduling
from beauty_formula.apps.services.tasks.expire_punctual_time_off import expire_punctual_time_off
from beauty_formula.apps.services.tasks.send_next_day_scheduling_reminders import send_next_day_scheduling_reminders

pytestmark = pytest.mark.django_db

S = Scheduling.SchedulingStatus


@pytest.fixture
def overdue(make_scheduling):
    return make_scheduling(status=S.CONFIRMED, scheduled_time=timezone.now() - timedelta(days=2))


def test_close_overdue_queues_only_overdue_confirmed(overdue, make_scheduling, celery_delay):
    make_scheduling(status=S.CONFIRMED, days_ahead=3)                                             # futuro
    make_scheduling(status=S.CONFIRMED, scheduled_time=timezone.now() - timedelta(hours=1))        # dentro da carência
    make_scheduling(status=S.CREATED, scheduled_time=timezone.now() - timedelta(days=3))           # não confirmado
    close_overdue_schedulings()
    celery_delay.assert_called_once_with(overdue.id)


def test_close_overdue_with_nothing_to_do(celery_delay):
    close_overdue_schedulings()
    celery_delay.assert_not_called()


def test_complete_overdue_scheduling_closes_it(overdue):
    complete_overdue_scheduling(overdue.id)
    overdue.refresh_from_db()
    assert overdue.status == S.COMPLETED


def test_complete_overdue_is_noop_when_already_closed(overdue):
    Scheduling.objects.filter(id=overdue.id).update(status=S.CANCELED, canceled_at=timezone.now())
    complete_overdue_scheduling(overdue.id)
    overdue.refresh_from_db()
    assert overdue.status == S.CANCELED


def test_next_day_reminders_fan_out(make_scheduling, celery_delay):
    tomorrow = make_scheduling(status=S.CONFIRMED, days_ahead=1)
    make_scheduling(status=S.CONFIRMED, days_ahead=4, hour=11)
    send_next_day_scheduling_reminders()
    queued = [c.args[0] for c in celery_delay.call_args_list]
    assert tomorrow.id in queued and len(queued) == 1


def _punctual(employee, *, ended_ago=None, ends_in=None):
    now = timezone.now()
    end = now - ended_ago if ended_ago else now + ends_in
    return EmployeeTimeOff.objects.create(
        employee=employee, block_type="medical", block_modality=EmployeeTimeOff.BlockModality.PUNCTUAL,
        start_datetime=end - timedelta(hours=1), end_datetime=end,
    )


def test_expire_deactivates_expired_punctual_block(employee):
    block = _punctual(employee, ended_ago=timedelta(minutes=5))
    expire_punctual_time_off(str(block.id))
    block.refresh_from_db()
    assert block.is_active is False


def test_expire_keeps_block_that_was_postponed(employee):
    block = _punctual(employee, ends_in=timedelta(days=2))
    expire_punctual_time_off(str(block.id))
    block.refresh_from_db()
    assert block.is_active is True


def test_expire_ignores_missing_or_recurring_blocks(employee):
    import uuid
    expire_punctual_time_off(str(uuid.uuid4()))  # não levanta
    recurring = EmployeeTimeOff.objects.create(
        employee=employee, block_type="lunch", block_modality=EmployeeTimeOff.BlockModality.RECURRING,
        weekday=1, start_time="12:00", end_time="13:00",
    )
    expire_punctual_time_off(str(recurring.id))
    recurring.refresh_from_db()
    assert recurring.is_active is True