"""
Repository de EmployeeAverageRating — agregado de leitura (cache) com a
média de avaliações por funcionário.

Não existe create/update/delete "manual" aqui: o único jeito de alterar
esse model é recalculando a média a partir das AverageRating existentes,
via `recalculate_employee_average_rating`. É chamado pelo service layer
(average_rating_service) sempre que uma avaliação relacionada ao
funcionário é criada, atualizada, excluída, autorizada ou tem a
autorização revogada.

Só entram no cálculo avaliações autorizadas (`is_authorized=True`) — é
o que fica visível publicamente, então é o que a média pública deve
refletir.
"""
from django.db import transaction
from django.db.models import Avg, Count

from beauty_formula.apps.accounts.models.employee import Employee
from beauty_formula.apps.services.models.average_rating import AverageRating
from beauty_formula.apps.services.models.employee_average_rating import EmployeeAverageRating


@transaction.atomic
def recalculate_employee_average_rating(employee: Employee) -> EmployeeAverageRating:
    """
    Recalcula média e total de avaliações autorizadas de um funcionário e
    persiste no agregado (via `EmployeeAverageRating.apply()`). Cria o
    agregado se ainda não existir (primeira avaliação do funcionário).
    """
    aggregate, _created = EmployeeAverageRating.objects.get_or_create(employee=employee)

    stats = AverageRating.objects.filter(employee=employee, is_authorized=True).aggregate(avg=Avg("rating"), total=Count("id"))
    
    average_rating = round(stats["avg"], 1) if stats["avg"] is not None else 0
    total_reviews = stats["total"] or 0

    aggregate.apply(average_rating=average_rating, total_reviews=total_reviews)
    return aggregate