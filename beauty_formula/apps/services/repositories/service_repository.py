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


UPDATABLE_SERVICE_FIELDS = {"name", "description", "price", "commission_percentage", "duration"}

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
def update_service(service: Service, **fields) -> Service:
    """
    Atualiza parcialmente um serviço.

    Só os campos presentes em `fields` são alterados — inclusive se o
    valor for `None` (ex: `description=None` limpa a descrição de
    propósito). Campos que o chamador não passou permanecem intocados.
    O chamador (camada de `services.py`) é quem decide quais campos
    entram aqui, tipicamente usando `payload.model_dump(exclude_unset=True)`
    pra distinguir "não veio no request" de "veio como null".
    """
    unknown = set(fields) - UPDATABLE_SERVICE_FIELDS
    if unknown:
        raise ValueError(f"Campos não atualizáveis em Service: {', '.join(sorted(unknown))}")

    if not fields:
        return service

    for field, value in fields.items():
        setattr(service, field, value)

    service.save()  # Service.save() já roda full_clean() internamente
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