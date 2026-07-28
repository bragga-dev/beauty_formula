# scheduling_repository.py
"""
Repository de Scheduling — funções de persistência (criação, atualização,
cancelamento, mudança de status e exclusão) de agendamentos no banco de dados.

Todas as funções aqui recebem valores já resolvidos (instâncias de model,
não IDs) — resolver IDs pra instâncias é responsabilidade da camada de
`services.py`, não daqui.
"""
from datetime import datetime
from typing import Optional

from django.db import transaction
from django.utils import timezone

from beauty_formula.apps.accounts.models.user import User
from beauty_formula.apps.services.models.scheduling import Scheduling
from beauty_formula.apps.services.models.service import Service
from beauty_formula.apps.accounts.models.client import Client
from beauty_formula.apps.accounts.models.employee import Employee


UPDATABLE_SCHEDULING_FIELDS = {"service", "employee", "scheduled_time", "notes"}


@transaction.atomic
def create_scheduling(
    *,
    service: Service,
    client: Client,
    employee: Employee,
    scheduled_time: datetime,
    notes: Optional[str] = None,
) -> Scheduling:
    """
    Cria um novo agendamento.
    
    O preço e duração são preenchidos automaticamente a partir do serviço
    no método save() do model. Roda full_clean() antes de salvar para
    validar conflitos de horário.
    """
    scheduling = Scheduling(
        service=service,
        client=client,
        employee=employee,
        scheduled_time=scheduled_time,
        notes=notes,
    )
    scheduling.save()  
    return scheduling


@transaction.atomic
def update_scheduling(scheduling: Scheduling, **fields) -> Scheduling:
    """
    Atualiza parcialmente um agendamento.

    Só os campos presentes em `fields` são alterados. O chamador
    (camada de `services.py`) é quem decide quais campos entram aqui,
    tipicamente usando `payload.model_dump(exclude_unset=True)` pra
    distinguir "não veio no request" de "veio como null".
    
    IMPORTANTE: Atualizar `scheduled_time` aciona a validação de conflito
    no model e pode levantar ValidationError se houver sobreposição.
    """
    unknown = set(fields) - UPDATABLE_SCHEDULING_FIELDS
    if unknown:
        raise ValueError(f"Campos não atualizáveis em Scheduling: {', '.join(sorted(unknown))}")

    if not fields:
        return scheduling

    for field, value in fields.items():
        setattr(scheduling, field, value)

    scheduling.save()  # save() já chama full_clean()
    return scheduling


@transaction.atomic
def cancel_scheduling(
    scheduling: Scheduling,
    reason: str,
    canceled_by: User,
) -> Scheduling:
    """
    Cancela um agendamento.

    Usa o método `cancel()` do model, que já trata de definir status,
    canceled_at, canceled_reason, canceled_by e is_active=False.
    """
    scheduling.cancel(reason, canceled_by)
    return scheduling


@transaction.atomic
def confirm_scheduling(scheduling: Scheduling) -> Scheduling:
    """Confirma um agendamento pendente."""
    scheduling.confirm()
    return scheduling


@transaction.atomic
def start_scheduling(scheduling: Scheduling) -> Scheduling:
    """Inicia o atendimento de um agendamento confirmado."""
    scheduling.start()
    return scheduling


@transaction.atomic
def complete_scheduling(scheduling: Scheduling) -> Scheduling:
    """Conclui o atendimento de um agendamento em andamento."""
    scheduling.complete()
    return scheduling


@transaction.atomic
def mark_scheduling_as_no_show(scheduling: Scheduling) -> Scheduling:
    """Marca um agendamento como não compareceu."""
    scheduling.mark_as_no_show()
    return scheduling


@transaction.atomic
def reactivate_scheduling(scheduling: Scheduling) -> Scheduling:
    """
    Reativa um agendamento cancelado ou no_show.
    
    CUIDADO: Use com extrema cautela. Reativar um agendamento cancelado
    pode causar conflitos de horário se o funcionário já tiver sido
    reagendado no mesmo período. A validação de conflito rodará no
    save() e pode levantar ValidationError.
    """
    scheduling.is_active = True
    scheduling.status = Scheduling.SchedulingStatus.PENDING
    scheduling.canceled_at = None
    scheduling.canceled_reason = None
    scheduling.canceled_by = None
    scheduling.save()
    return scheduling


@transaction.atomic
def delete_scheduling(scheduling: Scheduling) -> None:
    """
    Exclui um agendamento permanentemente do banco.

    Use com cautela — prefira `cancel_scheduling` na maioria dos casos,
    pois um DELETE aqui quebra qualquer referência histórica e não gera
    registro de cancelamento.
    """
    scheduling.delete()


@transaction.atomic
def delete_schedulings_by_client(client: Client) -> None:
    """
    Exclui todos os agendamentos de um cliente.

    Útil ao desativar um cliente completamente, ou durante migrações/
    limpeza de dados.
    """
    Scheduling.objects.filter(client=client).delete()


@transaction.atomic
def delete_schedulings_by_employee(employee: Employee) -> None:
    """
    Exclui todos os agendamentos de um funcionário.

    Útil ao desativar um funcionário completamente, ou durante migrações/
    limpeza de dados.
    """
    Scheduling.objects.filter(employee=employee).delete()


@transaction.atomic
def delete_schedulings_by_service(service: Service) -> None:
    """
    Exclui todos os agendamentos de um serviço.

    CUIDADO: Isso apaga o histórico de agendamentos. Prefira desativar
    o serviço em vez de deletar seus agendamentos.
    """
    Scheduling.objects.filter(service=service).delete()


@transaction.atomic
def delete_canceled_schedulings_older_than(days: int) -> int:
    """
    Exclui agendamentos cancelados ou no_show mais antigos que X dias.

    Útil para limpeza periódica de dados. Retorna o número de registros
    deletados.
    """
    cutoff = timezone.now() - timezone.timedelta(days=days)
    deleted, _ = Scheduling.objects.filter(
        status__in=[Scheduling.SchedulingStatus.CANCELED, Scheduling.SchedulingStatus.NO_SHOW],
        canceled_at__lt=cutoff,
    ).delete()
    return deleted