"""
Fixtures compartilhadas por TODOS os apps.

Objetivo: a suíte roda em qualquer máquina/CI só com Postgres — sem MinIO,
sem Redis, sem SMTP e sem Asaas de verdade.

- Storage de mídia  -> InMemoryStorage (antes, testes de foto tentavam
  conectar em http://minio:9000 e falhavam fora do Docker).
- E-mail            -> locmem.
- Celery            -> `Task.delay/apply_async` interceptados (nenhuma
  conexão com broker).
- Cache             -> limpo a cada teste (django-ratelimit usa o cache;
  sem isso um teste herda o contador do anterior e leva 429).
"""
import io
from datetime import time, timedelta
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client as DjangoTestClient
from django.test.client import BOUNDARY, MULTIPART_CONTENT, encode_multipart
from django.utils import timezone
from ninja_jwt.tokens import RefreshToken

from beauty_formula.apps.accounts.models import User
from beauty_formula.apps.accounts.models.client import Client
from beauty_formula.apps.accounts.models.employee import Employee
from beauty_formula.apps.accounts.models.manager import Manager
from beauty_formula.apps.services.models.employee_service import EmployeeService
from beauty_formula.apps.services.models.employee_works_hours import EmployeeWorkingHours
from beauty_formula.apps.services.models.service import Service


@pytest.fixture(autouse=True)
def _isolate_infra(settings):
    settings.STORAGES = {
        **settings.STORAGES,
        "default": {"BACKEND": "django.core.files.storage.InMemoryStorage"},
    }
    settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
    cache.clear()
    with patch("celery.app.task.Task.delay") as delay, patch("celery.app.task.Task.apply_async") as apply_async:
        yield SimpleNamespace(delay=delay, apply_async=apply_async)
    cache.clear()


@pytest.fixture
def celery_delay(_isolate_infra):
    """Mock de `Task.delay` — para asserir que uma task foi (ou não) disparada."""
    return _isolate_infra.delay


@pytest.fixture
def celery_apply_async(_isolate_infra):
    return _isolate_infra.apply_async


# ─────────────────────────────────────────────────────────────────────────────
# Usuários (já verificados: is_active + is_trusty)
# ─────────────────────────────────────────────────────────────────────────────

def _verified(user: User) -> User:
    user.is_active = True
    user.is_trusty = True
    user.save(update_fields=["is_active", "is_trusty"])
    return user


@pytest.fixture
def root_admin(db):
    return User.objects.create_superuser(email="admin@example.com", password="Admin12345!")


@pytest.fixture
def manager_user(db):
    user = _verified(User.objects.create_user(email="gerente@example.com", password="Senha12345!", role="manager"))
    Manager.objects.create(user=user, first_name="Gabi", last_name="Gerente")
    return user


@pytest.fixture
def verified_client(db):
    user = _verified(User.objects.create_user(email="cliente@example.com", password="Senha12345!", role="client"))
    Client.objects.create(user=user, first_name="Maria", last_name="Silva")
    return user


@pytest.fixture
def other_verified_client(db):
    user = _verified(User.objects.create_user(email="cliente2@example.com", password="Senha12345!", role="client"))
    Client.objects.create(user=user, first_name="Carla", last_name="Souza")
    return user


@pytest.fixture
def verified_employee(db):
    user = _verified(User.objects.create_user(email="funcionaria@example.com", password="Senha12345!", role="employee"))
    Employee.objects.create(user=user, first_name="Joana", last_name="Lima")
    return user


@pytest.fixture
def other_verified_employee(db):
    user = _verified(User.objects.create_user(email="funcionario2@example.com", password="Senha12345!", role="employee"))
    Employee.objects.create(user=user, first_name="Pedro", last_name="Alves")
    return user


@pytest.fixture
def unverified_client_user(db):
    user = User.objects.create_user(email="novo@example.com", password="Senha12345!", role="client")
    Client.objects.create(user=user, first_name="Nova", last_name="Cliente")
    return user


# ─────────────────────────────────────────────────────────────────────────────
# Catálogo / agenda
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def service(db):
    return Service.objects.create(name="Corte", price=Decimal("100.00"), duration=timedelta(minutes=60))


@pytest.fixture
def employee(verified_employee):
    return verified_employee.employee_profile


@pytest.fixture
def client_profile(verified_client):
    return verified_client.client_profile


@pytest.fixture
def employee_offers_service(employee, service):
    return EmployeeService.objects.create(employee=employee, service=service, is_active=True)


@pytest.fixture
def open_all_week(employee):
    """Expediente 08:00–18:00 todos os dias — agenda sempre aberta."""
    for weekday in range(7):
        EmployeeWorkingHours.objects.create(
            employee=employee, weekday=weekday, start_time=time(8, 0), end_time=time(18, 0),
        )
    return employee


def next_slot(days_ahead: int = 2, hour: int = 10):
    """Datetime aware, `days_ahead` dias à frente, em ponto, no fuso do projeto."""
    base = timezone.localtime(timezone.now()) + timedelta(days=days_ahead)
    return base.replace(hour=hour, minute=0, second=0, microsecond=0)


# ─────────────────────────────────────────────────────────────────────────────
# Cliente HTTP da API
# ─────────────────────────────────────────────────────────────────────────────

class ApiClient:
    """Wrapper fino sobre o test client do Django para /api/ (JSON + Bearer)."""

    def __init__(self):
        self._c = DjangoTestClient()

    @staticmethod
    def token_for(user: User) -> str:
        return str(RefreshToken.for_user(user).access_token)

    def _headers(self, user):
        return {"HTTP_AUTHORIZATION": f"Bearer {self.token_for(user)}"} if user else {}

    def get(self, path, user=None, **params):
        return self._c.get(f"/api{path}", data=params, **self._headers(user))

    def post(self, path, data=None, user=None, **extra):
        return self._c.post(f"/api{path}", data=data if data is not None else {}, content_type="application/json", **self._headers(user), **extra)

    def patch(self, path, data=None, user=None):
        return self._c.patch(f"/api{path}", data=data if data is not None else {}, content_type="application/json", **self._headers(user))

    def post_form(self, path, data, user=None):
        """multipart/form-data (upload de arquivos)."""
        return self._c.post(f"/api{path}", data=data, **self._headers(user))

    def patch_form(self, path, data, user=None):
        """PATCH multipart — o test client do Django só monta multipart sozinho para POST."""
        return self._c.generic(
            "PATCH", f"/api{path}", encode_multipart(BOUNDARY, data), MULTIPART_CONTENT, **self._headers(user),
        )

    def delete(self, path, user=None, data=None):
        if data is None:
            return self._c.delete(f"/api{path}", **self._headers(user))
        return self._c.delete(f"/api{path}", data=data, content_type="application/json", **self._headers(user))


@pytest.fixture
def api():
    return ApiClient()


def image_file(name: str = "foto.png", fmt: str = "PNG", size=(32, 32)) -> SimpleUploadedFile:
    """Imagem real (passa no validate_image_file) para testes de upload."""
    from PIL import Image

    buf = io.BytesIO()
    Image.new("RGB", size, (200, 50, 120)).save(buf, format=fmt)
    return SimpleUploadedFile(name, buf.getvalue(), content_type=f"image/{fmt.lower()}")


@pytest.fixture
def make_scheduling(client_profile, employee, service):
    """Fábrica de agendamentos direto no banco (sem passar pela API)."""
    from beauty_formula.apps.services.models.scheduling import Scheduling

    def _make(status=Scheduling.SchedulingStatus.CREATED, days_ahead=2, hour=10, **extra):
        data = {"service": service, "client": client_profile, "employee": employee,
                "scheduled_time": next_slot(days_ahead, hour), "status": status}
        data.update(extra)
        return Scheduling.objects.create(**data)

    return _make