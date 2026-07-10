"""
Client Repository — persistência de perfil Membro.
"""
from typing import Optional
from beauty_formula.apps.accounts.models.user import User
from beauty_formula.apps.accounts.models.client import Client
from beauty_formula.apps.accounts.schemas.client_schema import GenderEnum
from django.core.files import File

from typing import Optional

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
    client = Client(
        user=user,
        first_name=first_name,
        last_name=last_name,
        username=username,
        phone=phone,
        gender=gender,
        birth_date=birth_date,
        instagram=instagram,
        photo=photo,
    )
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

