"""
Queries de Produto — Funções para buscar e filtrar produtos.
"""
from typing import Optional, List
from uuid import UUID
from django.db.models import Q, QuerySet
from beauty_formula.apps.website.models.product_models import Product, DEFAULT_PRODUCT_PHOTO


# ═══════════════════════════════════════════════════════════════════════════════
# Listagem Geral
# ═══════════════════════════════════════════════════════════════════════════════

def get_all_products() -> QuerySet[Product]:
    """Retorna todos os produtos, sem filtro."""
    return Product.objects.all().order_by("name")


def get_active_products() -> QuerySet[Product]:
    """Retorna apenas PRODUTOS ativos."""
    return Product.objects.filter(is_active=True).order_by("name")


def get_inactive_products() -> QuerySet[Product]:
    """Retorna apenas PRODUTOS inativos (desativados)."""
    return Product.objects.filter(is_active=False)

# ═══════════════════════════════════════════════════════════════════════════════
# Buscas Básicas por ID
# ═══════════════════════════════════════════════════════════════════════════════

def get_product_by_id(product_id: UUID) -> Optional[Product]:
    """Retorna o produto pelo ID, ou None se não existir."""
    try:
        return Product.objects.filter(id=product_id).first()
    except Product.DoesNotExist:
        return None


def get_product_by_id_inactivate(product_id: UUID) -> Optional[Product]:
    """Retorna o produto pelo ID, que estejam inativos."""
    try:
        return Product.objects.filter(id=product_id, is_active=False).first()
    except Product.DoesNotExist:
        return None

def get_products_by_ids(product_ids: List[UUID]) -> QuerySet[Product]:
    """Retorna múltiplos produtos por uma lista de IDs."""
    if not product_ids:
        return Product.objects.none()
    return Product.objects.filter(id__in=product_ids)


# ═══════════════════════════════════════════════════════════════════════════════
# Buscas por Nome
# ══════════════════════╗
def get_product_by_name(name: str, exact: bool = True) -> Optional[Product]:
    """
    Retorna produto pelo nome.

    Args:
        name: Nome do produto
        exact: Se True, busca exata (case-insensitive); False busca contém
    """
    if not name:
        return None

    if exact:
        return Product.objects.filter(name__iexact=name).first()
    return Product.objects.filter(name__icontains=name).first()


def get_products_by_name_partial(name: str) -> QuerySet[Product]:
    """Retorna produtos cujo nome contenha o termo buscado."""
    if not name:
        return Product.objects.none()
    return Product.objects.filter(name__icontains=name)


def search_products(query: str) -> QuerySet[Product]:
    """Busca produtos em nome e descrição."""
    if not query:
        return Product.objects.none()
    return Product.objects.filter(
        Q(name__icontains=query) | Q(description__icontains=query)
    )


# ═══════════════════════════════════════════════════════════════════════════════
# Buscas por Preço
# ═══════════════════════════════════════════════════════════════════════════════

def get_products_by_price_range(
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
) -> QuerySet[Product]:
    """Retorna produtos dentro de uma faixa de preço."""
    q = Q()
    if min_price is not None:
        q &= Q(price__gte=min_price)
    if max_price is not None:
        q &= Q(price__lte=max_price)

    if not q:
        return Product.objects.all()
    return Product.objects.filter(q)


def get_cheapest_products(limit: int = 5) -> QuerySet[Product]:
    """Retorna os produtos mais baratos."""
    return Product.objects.order_by("price")[:limit]


def get_most_expensive_products(limit: int = 5) -> QuerySet[Product]:
    """Retorna os produtos mais caros."""
    return Product.objects.order_by("-price")[:limit]


# ═══════════════════════════════════════════════════════════════════════════════
# Buscas por Imagem
# ═══════════════════════════════════════════════════════════════════════════════

def get_products_with_custom_image() -> QuerySet[Product]:
    """Retorna produtos que possuem imagem própria (não usam a imagem padrão)."""
    return Product.objects.exclude(image=DEFAULT_PRODUCT_PHOTO)


def get_products_with_default_image() -> QuerySet[Product]:
    """Retorna produtos que ainda usam a imagem padrão."""
    return Product.objects.filter(image=DEFAULT_PRODUCT_PHOTO)


# ═══════════════════════════════════════════════════════════════════════════════
# Filtros Avançados
# ═══════════════════════════════════════════════════════════════════════════════

def filter_products(
    search: Optional[str] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    is_active: Optional[bool] = True,
    order_by: str = "name",
) -> QuerySet[Product]:

    q = Q()

    if search:
        q &= Q(name__icontains=search) | Q(description__icontains=search)

    if min_price is not None:
        q &= Q(price__gte=min_price)

    if max_price is not None:
        q &= Q(price__lte=max_price)

    if is_active is not None:
        q &= Q(is_active=is_active)

    qs = Product.objects.filter(q) if q else Product.objects.all()
    return qs.order_by(order_by)

# ═══════════════════════════════════════════════════════════════════════════════
# Utilitários
# ═══════════════════════════════════════════════════════════════════════════════

def validate_product_exists(product_id: UUID) -> bool:
    """Verifica se um produto existe."""
    return Product.objects.filter(id=product_id).exists()


def validate_product_name_available(name: str, exclude_id: Optional[UUID] = None) -> bool:
    """
    Verifica se o nome do produto está disponível (respeitando a
    UniqueConstraint do model). Usado antes de criar/renomear.
    """
    qs = Product.objects.filter(name__iexact=name)
    if exclude_id:
        qs = qs.exclude(id=exclude_id)
    return not qs.exists()