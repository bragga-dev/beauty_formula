"""
Queries de Scheduling — usado pelo cálculo de disponibilidade pra saber
quais horários do funcionário já estão ocupados.
"""
from datetime import date as date_type, timedelta
from uuid import UUID

from django.db.models import QuerySet

from beauty_formula.apps.services.models.scheduling import Scheduling

# Status que efetivamente ocupam a agenda do funcionário. Concluído/
# cancelado/no-show não bloqueiam novos horários.
BUSY_STATUSES = [
    Scheduling.SchedulingStatus.PENDING,
    Scheduling.SchedulingStatus.CONFIRMED,
    Scheduling.SchedulingStatus.IN_PROGRESS,
]


def get_active_schedulings_for_employee_on_date(employee_id: UUID, target_date: date_type) -> QuerySet[Scheduling]:
    """
    Retorna os agendamentos que podem ocupar a agenda do funcionário numa
    data específica.

    A janela de busca é levemente mais ampla que o próprio dia (pega
    também o dia anterior) pra não perder um agendamento que começou
    tarde da noite e termina depois da meia-noite. A subtração de
    intervalos feita depois (availability_selector) descarta qualquer
    coisa que não se sobreponha de verdade à data pedida.
    """
    return Scheduling.objects.filter(
        employee_id=employee_id,
        is_active=True,
        status__in=BUSY_STATUSES,
        scheduled_time__date__in=[target_date - timedelta(days=1), target_date],
    )