from __future__ import absolute_import, unicode_literals
import os
from celery import Celery

# Aponta para o módulo de settings do Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'beauty_formula.config.settings.dev')

app = Celery('beauty_formula')

# Lê configurações do Django (prefixadas com CELERY_)
app.config_from_object('django.conf:settings', namespace='CELERY')

# Descobre automaticamente tasks.py nos apps
app.autodiscover_tasks()