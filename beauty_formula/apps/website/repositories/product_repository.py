"""
Repository de Serviço — funções de persistência (criação, atualização,
ativação/desativação e exclusão) no banco de dados.

Todas as funções aqui recebem valores já no formato do model (ex: `duration`
como `timedelta`, não `duration_minutes`) — a conversão de payload de API
pra formato de model é responsabilidade da camada de `services.py`, não daqui.
"""
from datetime import timedelta
from decimal import Decimal
from typing import Optional
from uuid import UUID

from django.core.files.uploadedfile import UploadedFile
from django.db import transaction

from beauty_formula.apps.services.models.service import Service
from beauty_formula.apps.website.models.product_models import DEFAULT_PRODUCT_PHOTO, Product
from beauty_formula.apps.core.tasks.media import delete_old_media_file


UPDATABLE_PRODUCT_FIELDS = {"name", "description", "price", "stock", "is_active"}

@transaction.atomic
def create_product(*, name: str, price: Decimal, description: Optional[str] = None, stock: int, image: Optional[UploadedFile] = None) -> Product:
    product = Product(name=name, price=price, description=description, stock=stock, image=image,)
    if image is not None:
        product.image = image

    product.full_clean()
    product.save()
    return product


@transaction.atomic
def update_product(product: Product, **fields) -> Product:
    """
    Atualiza parcialmente um produto.

    Só os campos presentes em `fields` são alterados — inclusive se o
    valor for `None` (ex: `description=None` limpa a descrição de
    propósito). Campos que o chamador não passou permanecem intocados.
    O chamador (camada de `services.py`) é quem decide quais campos
    entram aqui, tipicamente usando `payload.model_dump(exclude_unset=True)`
    pra distinguir "não veio no request" de "veio como null".
    """
    unknown = set(fields) - UPDATABLE_PRODUCT_FIELDS
    if unknown:
        raise ValueError(f"Campos não atualizáveis em Product: {', '.join(sorted(unknown))}")

    if not fields:
        return product  # nada a fazer  

    for field, value in fields.items():
        setattr(product, field, value)

    product.save() 
    return product


@transaction.atomic
def set_product_image(product: Product, image: UploadedFile) -> Product:
    """Substitui a imagem de um produto existente.

    A imagem antiga é removida do MinIO em background (Celery) em vez de
    bloquear a request com um DELETE síncrono antes do upload da nova.
    """
    old_name = product.image.name if product.image and product.image.name != DEFAULT_PRODUCT_PHOTO else None
    product.image = image
    product.full_clean()
    product.save()
    if old_name:
        delete_old_media_file.delay(old_name)
    return product


@transaction.atomic
def remove_product_image(product: Product) -> Product:
    """Remove a imagem de um produto, voltando para a imagem padrão."""
    old_name = product.image.name if product.image and product.image.name != DEFAULT_PRODUCT_PHOTO else None
    product.image = DEFAULT_PRODUCT_PHOTO
    product.save(update_fields=["image"])
    if old_name:
        delete_old_media_file.delay(old_name)
    return product


@transaction.atomic
def activate_product(product: Product) -> Product:
    """Reativa um produto desativado."""
    product.is_active = True
    product.save(update_fields=["is_active"])
    return product


@transaction.atomic
def deactivate_product(product: Product) -> Product:
    """
    Desativa um produto (soft delete). Preferível a apagar de verdade —
    mantém histórico de agendamentos que referenciam esse produto.
    """
    product.is_active = False
    product.save(update_fields=["is_active"])
    return product


@transaction.atomic
def delete_product(product: Product) -> None:
    """
    Exclui um produto permanentemente do banco.
    Use com cautela — prefira `deactivate_product` na maioria dos casos,
    pois um DELETE aqui quebra qualquer FK de agendamento apontando pra
    esse produto (dependendo do on_delete configurado no model relacionado).
    """
    product.delete()