from decimal import Decimal
from typing import Optional
import uuid

from ninja import UploadedFile
from django.db.models  import QuerySet
from beauty_formula.apps.website.models.product_models import Product
from beauty_formula.apps.website.repositories.product_repository import (
    create_product, 
    update_product,
    delete_product,
    deactivate_product,
    activate_product,
    set_product_image,
    remove_product_image,
    
    )
from beauty_formula.apps.website.schemas.product_schema import (
    ProductCreateIn, 
    ProductUpdateIn,
    ProductOut,
    ProductListOut,
    ProductPrivateOut,
    ProductDetailOut,
    )
from beauty_formula.apps.website.selectors.product_selector import (
    get_product_by_id,
    get_all_products,
    get_active_products,
    get_inactive_products,

)

from beauty_formula.apps.core.exceptions.product_exception import (
    ProductNotFound,
)






def create_product_for_admin(data: ProductCreateIn, image: Optional[UploadedFile] = None) -> ProductOut:
    """
    Cria um produto com todos os campos necessários para o admin.
    """
    product = create_product(
                       name=data.name,
                       price=data.price,
                       image=image,
                       stock=data.stock,
                       description=data.description
        )
    return ProductOut.from_orm(product)
    




def update_product_for_admin(product_id: uuid.UUID, payload: ProductUpdateIn) -> ProductOut:
    """
    Atualiza parcialmente um produto com todos os campos necessários para o admin.
    """
    product = get_product_by_id(product_id=product_id)
    if product is None:
        raise ProductNotFound()

    fields = payload.model_dump(exclude_unset=True)
    updated = update_product(product=product, **fields)
    return ProductOut.from_orm(updated)    




def list_all_public_products() -> QuerySet[Product]:
    """Lista todos os produtos ativos disponíveis para o público."""
    return get_active_products()

def list_all_private_products() -> QuerySet[Product]:
    """Lista todos os produtos ativos e inativos, apenas Admins podem acessar esse recurso"""
    return get_all_products()


def update_image_product_for_admin(product_id: uuid.UUID, image: UploadedFile) -> ProductOut:
    """Substitui a imagem de um produto existente, apenas Admins podem fazer essa ação"""
    product = get_product_by_id(product_id=product_id)
    if product is None:
        raise ProductNotFound()
    updated_product = set_product_image(product=product, image=image)
    return ProductOut.from_orm(updated_product)


def remove_image_product_for_admin(product_id: uuid.UUID) -> ProductOut:
    """Remove a imagem de um produto, voltando para a imagem padrão. Apenas Admins podem fazer essa ação"""
    product = get_product_by_id(product_id=product_id)
    if product is None:
        raise ProductNotFound()
    updated_product = remove_product_image(product=product)
    return ProductOut.from_orm(updated_product)



def detail_product(product_id: uuid.UUID) -> ProductDetailOut:
    """Exibe detalhes deum produto"""
    product = get_product_by_id(product_id=product_id)
    if product is None:
        raise ProductNotFound()
    return product



def delete_product_for_admin(product_id:uuid.UUID) -> None:
    """Deleta produtos, apenas admins podem fazer essa ação"""
    product = get_product_by_id(product_id=product_id)
    if product is None:
        raise ProductNotFound()
    delete_product(product=product)


def deactivate_product_for_admin(product_id: uuid.UUID) -> ProductOut:
    """Desativa um produto, apenas Admin pode fazer essa ação"""
    product = get_product_by_id(product_id=product_id)
    if product is None:
        raise ProductNotFound()

    updated_product = deactivate_product(product=product)
    return ProductOut.from_orm(updated_product)


def activate_product_for_admin(product_id: uuid.UUID) -> ProductOut:
    """Ativa Produto, apenas Admins podem fazer essa ação"""
    product = get_product_by_id(product_id=product_id)
    if product is None:
        raise ProductNotFound()
    updated_product = activate_product(product=product)
    return ProductOut.from_orm(updated_product)