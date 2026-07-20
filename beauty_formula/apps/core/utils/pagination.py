"""
Paginação genérica — compatível com schemas que usam from_orm customizado.

Por que não usar @paginate do ninja diretamente?
O ninja.pagination exige que o endpoint retorne o queryset puro para ele serializar.
Nossos schemas usam from_orm() customizado (ex: ChurchOut.from_orm, MemberOut.from_orm),
então precisamos serializar antes de paginar.

Uso:
    from ecclesia.apps.users.utils.pagination import paginate_queryset, PageOut

    @router.get("/", response=PageOut[ChurchOut])
    def list_churches(request, page: int = 1, page_size: int = 20):
        qs = get_all_churches().select_related("user")
        return paginate_queryset(qs, page, page_size, ChurchOut.from_orm)
"""

import math
from typing import TypeVar, Generic, List, Callable, Any
from ninja import Schema
from django.db.models import QuerySet

T = TypeVar("T")
from beauty_formula.apps.core.schemas.deafult_schema import PageOut

# Limites de segurança
PAGE_SIZE_DEFAULT = 20
PAGE_SIZE_MAX = 100



def paginate_queryset(
    qs: QuerySet,
    page: int,
    page_size: int,
    serializer: Callable[[Any], T],
) -> PageOut[T]:
    """
    Pagina um queryset e serializa cada item com o callable informado.

    Args:
        qs:          QuerySet a paginar (pode já ter select_related/filter)
        page:        número da página (começa em 1)
        page_size:   itens por página (máx PAGE_SIZE_MAX)
        serializer:  callable que recebe uma instância e retorna o schema
                     ex: ChurchOut.from_orm, MemberOut.from_orm, lambda x: x

    Returns:
        PageOut com items serializados e metadados de paginação.
    """
    # Sanitização
    page = max(1, page)
    page_size = max(1, min(page_size, PAGE_SIZE_MAX))

    total = qs.count()
    pages = math.ceil(total / page_size) if total else 1

    offset = (page - 1) * page_size
    items = qs[offset: offset + page_size]

    return PageOut(
        items=[serializer(obj) for obj in items],
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )