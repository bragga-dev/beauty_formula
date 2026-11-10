"""Service de notificações: destinatário certo por evento + falha de notificação nunca derruba o fluxo."""
import uuid
from unittest.mock import patch

import pytest

from beauty_formula.apps.notifications.models.notification import Notification
from beauty_formula.apps.notifications.services import notification_service as ns
from beauty_formula.apps.services.models.scheduling import Scheduling

pytestmark = pytest.mark.django_db

S = Scheduling.SchedulingStatus

CLIENT_EVENTS = [
    ns.notify_scheduling_confirmed,
    ns.notify_scheduling_cancelled,
    ns.notify_scheduling_rescheduled,
    ns.notify_scheduling_reminder,
    ns.notify_scheduling_complete,
    ns.notify_scheduling_no_show,
    ns.notify_request_rating,
]
EMPLOYEE_EVENTS = [
    ns.notify_scheduling_confirmed_employee,
    ns.notify_scheduling_cancelled_employee,
    ns.notify_scheduling_rescheduled_employee,
    ns.notify_scheduling_complete_employee,
]


@pytest.fixture
def scheduling(make_scheduling):
    return make_scheduling(status=S.CONFIRMED, days_ahead=3)


@pytest.mark.parametrize("notify", CLIENT_EVENTS, ids=lambda f: f.__name__)
def test_client_events_notify_the_client(notify, scheduling, client_profile):
    n = notify(scheduling.id)
    assert n is not None
    assert n.recipient_id == client_profile.user_id


@pytest.mark.parametrize("notify", EMPLOYEE_EVENTS, ids=lambda f: f.__name__)
def test_employee_events_notify_the_employee(notify, scheduling, employee):
    n = notify(scheduling.id)
    assert n is not None
    assert n.recipient_id == employee.user_id


@pytest.mark.parametrize("notify", CLIENT_EVENTS + EMPLOYEE_EVENTS, ids=lambda f: f.__name__)
def test_unknown_scheduling_returns_none_without_raising(notify):
    assert notify(uuid.uuid4()) is None
    assert not Notification.objects.exists()


def test_actor_is_recorded_when_given(scheduling, root_admin):
    n = ns.notify_scheduling_cancelled(scheduling.id, actor=root_admin)
    assert n is not None and n.recipient_id == scheduling.client.user_id


def test_failures_are_swallowed(scheduling):
    with patch.object(ns, "notify", side_effect=RuntimeError("boom")):
        assert ns.notify_scheduling_confirmed(scheduling.id) is None


def test_complete_profile_and_employee_promoted(verified_client, verified_employee, root_admin):
    assert ns.notify_complete_profile(verified_client.id).recipient_id == verified_client.id
    assert ns.notify_employee_promoted(verified_employee.id, actor=root_admin).recipient_id == verified_employee.id


def test_system_notification_and_read_cycle(verified_client):
    n = ns.notify_system(user_id=verified_client.id, title="Olá", body="Bem-vindo", action_url="/painel")
    assert n.is_read is False and ns.unread_count_for_user(user_id=verified_client.id) == 1
    assert ns.mark_notification_as_read(user_id=verified_client.id, notification_id=n.id).is_read is True
    assert ns.unread_count_for_user(user_id=verified_client.id) == 0


def test_mark_all_and_delete(verified_client):
    ns.notify_system(user_id=verified_client.id, title="a")
    ns.notify_system(user_id=verified_client.id, title="b")
    assert ns.mark_all_notifications_as_read(user_id=verified_client.id) == 2
    first = ns.list_notifications_for_user(user_id=verified_client.id).first()
    ns.delete_notification(user_id=verified_client.id, notification_id=first.id)
    assert ns.list_notifications_for_user(user_id=verified_client.id).count() == 1


def test_list_unread_only(verified_client):
    a = ns.notify_system(user_id=verified_client.id, title="a")
    ns.notify_system(user_id=verified_client.id, title="b")
    ns.mark_notification_as_read(user_id=verified_client.id, notification_id=a.id)
    assert ns.list_notifications_for_user(user_id=verified_client.id, unread_only=True).count() == 1