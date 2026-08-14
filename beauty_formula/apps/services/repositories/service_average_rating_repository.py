"""
Repository de ServiceAverageRating — agregado de leitura (cache) com a
média de avaliações por serviço.

Não existe create/update/delete "manual" aqui: o único jeito de alterar
esse model é recalculando a média a partir das AverageRating existentes,
via `recalculate_service_average_rating`. É chamado pelo service layer
(average_rating_service) sempre que uma avaliação relacionada ao serviço
é criada, atualizada, excluída, autorizada ou tem a autorização revogada.

Só entram no cálculo avaliações autorizadas (`is_authorized=True`) — é
o que fica visível publicamente, então é o que a média pública deve
refletir.
"""
from django.db import transaction
from django.db.models import Avg, Count

from beauty_formula.apps.services.models.average_rating import AverageRating
from beauty_formula.apps.services.models.service import Service
from beauty_formula.apps.services.models.service_average_rating import ServiceAverageRating


@transaction.atomic
def recalculate_service_average_rating(service: Service) -> ServiceAverageRating:
    """
    Recalcula média e total de avaliações autorizadas de um serviço e
    persiste no agregado (via `ServiceAverageRating.apply()`). Cria o
    agregado se ainda não existir (primeira avaliação do serviço).
    """
    aggregate, _created = ServiceAverageRating.objects.get_or_create(service=service)

    stats = AverageRating.objects.filter(service=service, is_authorized=True).aggregate(
        avg=Avg("rating"), total=Count("id")
    )
    average_rating = round(stats["avg"], 1) if stats["avg"] is not None else 0
    total_reviews = stats["total"] or 0

    aggregate.apply(average_rating=average_rating, total_reviews=total_reviews)
    return aggregate