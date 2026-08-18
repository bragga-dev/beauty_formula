from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch

import pytest
from django.utils import timezone

from beauty_formula.apps.accounts.models import User
from beauty_formula.apps.accounts.models.client import Client
from beauty_formula.apps.accounts.models.employee import Employee
from beauty_formula.apps.payment.models.payment_model import Payment
from beauty_formula.apps.services.models.scheduling import Scheduling
from beauty_formula.apps.services.models.service import Service


@pytest.fixture(autouse=True)
def no_celery_broker(settings):
    """
    Nenhum teste aqui quer de fato falar com um broker (RabbitMQ/Redis)
    nem disparar e-mail de verdade — o que importa é a mudança de estado
    no banco (Payment/Scheduling), não o side-effect assíncrono.
    `Task.delay` é interceptado direto, então nem chega a tentar abrir
    conexão com o broker (CELERY_TASK_ALWAYS_EAGER faria o corpo da task
    rodar de verdade, o que aqui dispararia SMTP real).
    """
    with patch("celery.app.task.Task.delay"), patch("celery.app.task.Task.apply_async"):
        yield


@pytest.fixture
def client_user():
    return User.objects.create_user(email="cliente@example.com", password="password123", role="client")


@pytest.fixture
def client_profile(client_user):
    return Client.objects.create(user=client_user, first_name="Maria", last_name="Silva")


@pytest.fixture
def employee_user():
    return User.objects.create_user(email="funcionaria@example.com", password="password123", role="employee")


@pytest.fixture
def employee_profile(employee_user):
    return Employee.objects.create(user=employee_user, first_name="Joana", last_name="Souza")


@pytest.fixture
def service():
    return Service.objects.create(name="Corte", price=Decimal("100.00"), duration=timedelta(minutes=60))


@pytest.fixture
def scheduling(client_profile, employee_profile, service):
    return Scheduling.objects.create(
        service=service,
        client=client_profile,
        employee=employee_profile,
        scheduled_time=timezone.now() + timedelta(days=1),
        status=Scheduling.SchedulingStatus.CREATED,
    )


@pytest.fixture
def confirmed_scheduling(client_profile, employee_profile, service):
    scheduling = Scheduling.objects.create(
        service=service,
        client=client_profile,
        employee=employee_profile,
        scheduled_time=timezone.now() + timedelta(days=1),
        status=Scheduling.SchedulingStatus.CREATED,
    )
    scheduling.confirm()
    return scheduling


@pytest.fixture
def pending_payment(scheduling):
    return Payment.objects.create(
        scheduling=scheduling,
        client=scheduling.client,
        billing_type=Payment.PaymentMode.PIX,
        value=Decimal("100.00"),
        due_date=timezone.now().date() + timedelta(days=1),
        description="Corte - Maria Silva",
        asaas_payment_id="pay_123",
        asaas_customer_id="cus_salon",
        status=Payment.PaymentStatus.PENDING,
    )