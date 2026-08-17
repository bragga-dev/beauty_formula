from __future__ import absolute_import, unicode_literals
import os
from celery import Celery
from celery.schedules import crontab

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'beauty_formula.config.settings.dev')

app = Celery('beauty_formula')

app.config_from_object('django.conf:settings', namespace='CELERY')

app.autodiscover_tasks()

app.conf.beat_schedule = {
    "send-next-day-scheduling-reminders": {
        "task": "beauty_formula.apps.services.tasks.send_next_day_scheduling_reminders.send_next_day_scheduling_reminders",
        "schedule": crontab(hour=6, minute=0),
    },
}