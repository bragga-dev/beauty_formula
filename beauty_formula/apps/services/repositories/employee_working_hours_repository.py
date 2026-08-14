from django.db import transaction

from beauty_formula.apps.services.models.employee_works_hours import EmployeeWorkingHours


@transaction.atomic
def create_employee_working_hours(employee, weekday: int, start_time, end_time) -> EmployeeWorkingHours:
    """
    Cria um turno de trabalho pro funcionário. `save()` já roda
    `full_clean()` — overlap com outro turno do mesmo dia e
    `start_time < end_time` são validados no model, não aqui.
    """
    return EmployeeWorkingHours.objects.create(employee=employee, weekday=weekday, start_time=start_time, end_time=end_time)


@transaction.atomic
def update_employee_working_hours(working_hours: EmployeeWorkingHours, weekday: int = None, start_time=None, end_time=None) -> EmployeeWorkingHours:
    """
    Atualização parcial — só altera os campos informados (None = mantém
    o valor atual). A validação de overlap/start<end roda de novo no
    save(), contra os outros turnos já existentes.
    """
    if weekday is not None:
        working_hours.weekday = weekday
    if start_time is not None:
        working_hours.start_time = start_time
    if end_time is not None:
        working_hours.end_time = end_time

    working_hours.save()
    return working_hours


@transaction.atomic
def delete_employee_working_hours(working_hours: EmployeeWorkingHours) -> None:
    """
    Exclui o turno permanentemente. Diferente de EmployeeService, não
    existe soft-delete aqui — não há histórico a preservar num horário
    de trabalho, é só a grade da semana.
    """
    working_hours.delete()