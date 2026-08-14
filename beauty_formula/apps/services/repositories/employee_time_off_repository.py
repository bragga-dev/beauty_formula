"""
Repository de EmployeeTimeOff — funções de persistência (criação,
atualização e exclusão) de bloqueios de horário (recorrentes ou
pontuais) de um funcionário.

Todas as funções aqui recebem valores já resolvidos (instâncias de
model) — resolver `employee_id` pra instância é responsabilidade da
camada de `services.py`, não daqui.
"""
from datetime import time, datetime
from typing import Optional
from uuid import UUID

from django.db import transaction

from beauty_formula.apps.services.models.employee_time_off import EmployeeTimeOff
from beauty_formula.apps.accounts.models.employee import Employee


UPDATABLE_EMPLOYEE_TIME_OFF_FIELDS = {
    "block_type", "block_modality", "weekday", "start_time", "end_time", "start_datetime", "end_datetime"
}

@transaction.atomic
def create_time_off(
    *,
    employee: Employee,
    block_type: str,
    block_modality: str,
    weekday: Optional[int] = None,
    start_time: Optional[time] = None,
    end_time: Optional[time] = None,
    start_datetime: Optional[datetime] = None,
    end_datetime: Optional[datetime] = None,
) -> EmployeeTimeOff:
    """
    Cria um bloqueio de horário para um funcionário.

    `block_modality` é quem decide a validação no model (não mais uma
    inferência a partir de quais campos vieram preenchidos) — quem
    chama essa função (services/employee_time_off_service.py) já sabe
    qual modalidade quer, já que agora são duas rotas exclusivas de
    criação (recorrente vs pontual), não uma genérica.

    O save() já roda full_clean() — validações de overlap e regras de
    negócio são feitas no model, não aqui.
    """
    time_off = EmployeeTimeOff(
        employee=employee,
        block_type=block_type,
        block_modality=block_modality,
        weekday=weekday,
        start_time=start_time,
        end_time=end_time,
        start_datetime=start_datetime,
        end_datetime=end_datetime,
    )
    time_off.save()
    return time_off


@transaction.atomic
def update_time_off(time_off: EmployeeTimeOff, **fields) -> EmployeeTimeOff:
    """
    Atualiza parcialmente um bloqueio de horário.

    None = mantém o valor atual — por isso só aplica os campos cujo
    valor não é None. Sem esse filtro, qualquer PATCH parcial (ex: só
    trocar block_type) reseta todos os outros campos pra None, o que
    imediatamente quebra a validação XOR do model (nem recorrente nem
    pontual) no save() seguinte.
    """
    unknown = set(fields) - UPDATABLE_EMPLOYEE_TIME_OFF_FIELDS
    if unknown:
        raise ValueError(f"Campos não atualizáveis em Folga do funcionário: {', '.join(sorted(unknown))}")

    fields_to_apply = {field: value for field, value in fields.items() if value is not None}
    if not fields_to_apply:
        return time_off

    for field, value in fields_to_apply.items():
        setattr(time_off, field, value)

    time_off.save() 
    return time_off


@transaction.atomic
def delete_time_off(time_off: EmployeeTimeOff) -> None:
    """
    Exclui um bloqueio permanentemente do banco.

    Use com cautela — prefira apenas desativar/ignorar bloqueios na
    maioria dos casos, mas aqui não tem soft delete porque um bloqueio
    é um registro de configuração, não um agendamento com histórico.
    """
    time_off.delete()


@transaction.atomic
def delete_time_off_by_employee(employee: Employee) -> None:
    """
    Exclui todos os bloqueios de um funcionário.

    Útil ao desativar um funcionário completamente, ou durante
    migrações/limpeza de dados.
    """
    EmployeeTimeOff.objects.filter(employee=employee).delete()


@transaction.atomic
def delete_recurring_time_off_by_employee(employee: Employee) -> None:
    """
    Exclui todos os bloqueios recorrentes de um funcionário.
    """
    EmployeeTimeOff.objects.filter(employee=employee, weekday__isnull=False).delete()


@transaction.atomic
def delete_punctual_time_off_by_employee(employee: Employee) -> None:
    """
    Exclui todos os bloqueios pontuais de um funcionário.
    """
    EmployeeTimeOff.objects.filter(employee=employee, start_datetime__isnull=False).delete()


@transaction.atomic
def delete_time_off_by_block_type(employee: Employee, block_type: str) -> None:
    """
    Exclui todos os bloqueios de um funcionário por tipo específico.
    """
    EmployeeTimeOff.objects.filter(employee=employee, block_type=block_type).delete()