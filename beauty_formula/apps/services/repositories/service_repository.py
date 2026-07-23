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

from beauty_formula.apps.services.models.service import DEFAULT_SERVICE_PHOTO, Service


@transaction.atomic
def create_service(
    *,
    name: str,
    price: Decimal,
    description: Optional[str] = None,
    commission_percentage: Decimal = Decimal("70"),
    duration: timedelta = timedelta(minutes=30),
    image: Optional[UploadedFile] = None,
) -> Service:
    """Cria um novo serviço. Roda full_clean() antes de salvar."""
    service = Service(
        name=name,
        price=price,
        description=description,
        commission_percentage=commission_percentage,
        duration=duration,
    )
    if image is not None:
        service.image = image

    service.full_clean()
    service.save()
    return service


@transaction.atomic
def update_service(
    service: Service,
    *,
    name: Optional[str] = None,
    description: Optional[str] = None,
    price: Optional[Decimal] = None,
    commission_percentage: Optional[Decimal] = None,
    duration: Optional[timedelta] = None,
) -> Service:
    """
    Atualiza campos de um serviço existente. Apenas os campos passados
    (diferentes de None) são alterados — atualização parcial.
    """
    if name is not None:
        service.name = name
    if description is not None:
        service.description = description
    if price is not None:
        service.price = price
    if commission_percentage is not None:
        service.commission_percentage = commission_percentage
    if duration is not None:
        service.duration = duration

    service.full_clean()
    service.save()
    return service


@transaction.atomic
def set_service_image(service: Service, image: UploadedFile) -> Service:
    """Substitui a imagem de um serviço existente."""
    if service.image and service.image.name != DEFAULT_SERVICE_PHOTO:
        service.image.delete(save=False)
    service.image = image
    service.full_clean()
    service.save()
    return service


@transaction.atomic
def remove_service_image(service: Service) -> Service:
    """Remove a imagem de um serviço, voltando para a imagem padrão."""
    if service.image and service.image.name != DEFAULT_SERVICE_PHOTO:
        service.image.delete(save=False)
    service.image = DEFAULT_SERVICE_PHOTO
    service.save(update_fields=["image"])
    return service


@transaction.atomic
def activate_service(service: Service) -> Service:
    """Reativa um serviço desativado."""
    service.is_active = True
    service.save(update_fields=["is_active"])
    return service


@transaction.atomic
def deactivate_service(service: Service) -> Service:
    """
    Desativa um serviço (soft delete). Preferível a apagar de verdade —
    mantém histórico de agendamentos que referenciam esse serviço.
    """
    service.is_active = False
    service.save(update_fields=["is_active"])
    return service


@transaction.atomic
def delete_service(service: Service) -> None:
    """
    Exclui um serviço permanentemente do banco.
    Use com cautela — prefira `deactivate_service` na maioria dos casos,
    pois um DELETE aqui quebra qualquer FK de agendamento apontando pra
    esse serviço (dependendo do on_delete configurado no model relacionado).
    """
    service.delete()