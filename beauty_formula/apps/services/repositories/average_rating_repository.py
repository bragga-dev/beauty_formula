"""
Repository de AverageRating — funções de persistência (criação,
atualização, autorização e exclusão) da avaliação real deixada pelo
cliente sobre um atendimento concluído.

Como no repository de Service, essas funções recebem valores já resolvidos
(instâncias de model, não IDs) — resolver `scheduling_id`/`service_id`/
`employee_id`/`client_id` pra instância é responsabilidade da camada de
`services.py`, não daqui.
"""
from typing import Optional

from django.db import transaction

from beauty_formula.apps.accounts.models.client import Client
from beauty_formula.apps.accounts.models.employee import Employee
from beauty_formula.apps.services.models.average_rating import AverageRating
from beauty_formula.apps.services.models.scheduling import Scheduling
from beauty_formula.apps.services.models.service import Service

AVERAGE_RATING_FIELDS = {"comment", "rating"}


@transaction.atomic
def create_average_rating(
    *,
    scheduling: Scheduling,
    service: Service,
    employee: Employee,
    client: Client,
    rating: int,
    comment: Optional[str] = None,
) -> AverageRating:
    """
    Cria a avaliação de um agendamento concluído. Roda full_clean() antes
    de salvar (via AverageRating.save()) — garante que o agendamento está
    CONCLUÍDO e que client/employee/service batem com o agendamento.
    """
    average_rating = AverageRating(
        scheduling=scheduling,
        service=service,
        employee=employee,
        client=client,
        rating=rating,
        comment=comment,
    )
    average_rating.save()
    return average_rating


@transaction.atomic
def update_rating(average_rating: AverageRating, **fields) -> AverageRating:
    """
    Atualiza parcialmente uma avaliação. Só `rating` e `comment` podem ser
    alterados pelo cliente — os campos denormalizados (scheduling/client/
    employee/service) e `is_authorized` não passam por aqui.
    """
    unknown = set(fields) - AVERAGE_RATING_FIELDS
    if unknown:
        raise ValueError(f"Campos não atualizáveis na Avaliação: {', '.join(sorted(unknown))}")

    if not fields:
        return average_rating

    for field, value in fields.items():
        setattr(average_rating, field, value)

    average_rating.save()
    return average_rating


@transaction.atomic
def authorize_rating(average_rating: AverageRating) -> AverageRating:
    """Autoriza a exibição pública da avaliação (ex: moderação aprovou)."""
    average_rating.is_authorized = True
    average_rating.save(update_fields=["is_authorized", "updated_at"])
    return average_rating


@transaction.atomic
def revoke_rating_authorization(average_rating: AverageRating) -> AverageRating:
    """Revoga a autorização de exibição pública da avaliação."""
    average_rating.is_authorized = False
    average_rating.save(update_fields=["is_authorized", "updated_at"])
    return average_rating


@transaction.atomic
def delete_average_rating(average_rating: AverageRating) -> None:
    """Exclui a avaliação permanentemente do banco."""
    average_rating.delete()