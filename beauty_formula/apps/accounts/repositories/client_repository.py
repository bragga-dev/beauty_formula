"""
Client Repository — persistência de perfil Membro.
"""
from typing import Optional
from beauty_formula.apps.accounts.models.user import User
from beauty_formula.apps.accounts.models.client import Client
from beauty_formula.apps.accounts.schemas.client_schema import GenderEnum
from django.core.files import File
from django.core.files.uploadedfile import InMemoryUploadedFile
from beauty_formula.apps.core.tasks.media import delete_old_media_file


def create_client(
    user: User,
    first_name: Optional[str] = None,
    last_name: Optional[str] = None,
    username: Optional[str] = None,
    phone: Optional[str] = None,
    gender: Optional[GenderEnum] = None,
    birth_date: Optional[str] = None,
    instagram: Optional[str] = None,
    photo: Optional[File] = None,
) -> Client:
    fields = {
        "first_name": first_name,
        "last_name": last_name,
        "username": username,
        "phone": phone,
        "gender": gender,
        "birth_date": birth_date,
        "instagram": instagram,
        "photo": photo,
    }
    fields = {k: v for k, v in fields.items() if v is not None}

    client = Client(user=user, **fields)
    client.save()
    return client




def update_client(client: Client, **fields) -> Client:
    for attr, value in fields.items():
        if value is not None:
            setattr(client, attr, value)
    client.full_clean()   
    client.save()
    return client


def delete_client(client: Client) -> None:
    client.delete()




def set_client_photo(client: Client, photo: InMemoryUploadedFile) -> Client:
    old_name = client.photo.name if client.photo and client.photo.name != "default/client_img.jpg" else None
    client.photo = photo
    client.save(update_fields=["photo"])
    if old_name:
        delete_old_media_file.delay(old_name)
    return client


def remove_client_photo(client: Client) -> Client:
    old_name = client.photo.name if client.photo and client.photo.name != "default/client_img.jpg" else None
    client.photo = "default/client_img.jpg"
    client.save(update_fields=["photo"])
    if old_name:
        delete_old_media_file.delay(old_name)
    return client


def set_client_asaas_customer_id(client: Client, asaas_customer_id: str) -> Client:
    """
    Grava o customer criado na Asaas na primeira cobrança via cartão do
    cliente, pra reaproveitar nas próximas — evita pedir CPF de novo.
    """
    client.asaas_customer_id = asaas_customer_id
    client.save(update_fields=["asaas_customer_id"])
    return client