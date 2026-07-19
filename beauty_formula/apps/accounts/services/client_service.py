



import uuid
from ninja import UploadedFile
from django.core.exceptions import ValidationError as DjangoValidationError
from beauty_formula.apps.core.validators.image_validator import validate_image_file
from beauty_formula.apps.accounts.repositories.client_repository import set_client_photo, remove_client_photo
from beauty_formula.apps.accounts.schemas.client_schema import ClientOut
from beauty_formula.apps.accounts.selectors.client_selector import get_client_by_user_id
from beauty_formula.apps.core.exceptions.user import UserNotFound
from beauty_formula.apps.core.exceptions.permissions import PermissionDenied
from beauty_formula.apps.accounts.models.user import User
from beauty_formula.apps.core.exceptions.media import InvalidImageFile

def upload_client_profile_photo(user: User, photo: UploadedFile) -> ClientOut:
    """
    Faz upload/substituição da foto do Cliente logado.

    `user` já vem autenticado de request.auth (ClientOnlyAuth já fez a query
    do User) — não recarregamos o User, só usamos seu id/role em memória.
    A validação da imagem é explícita aqui (fail-fast, sem tocar o banco se
    for inválida); o full_clean() do model ainda roda como segunda camada
    de segurança, mas não é mais a única validação.
    """
    if user.role != User.UserRole.CLIENT:
        raise PermissionDenied("Apenas clientes podem atualizar esta foto.")

    client = get_client_by_user_id(user.id)
    if not client:
        raise UserNotFound("Cliente não encontrado.")

    try:
        validate_image_file(photo)
    except DjangoValidationError as e:
        raise InvalidImageFile(e.messages[0] if getattr(e, "messages", None) else str(e))

    updated_client = set_client_photo(client=client, photo=photo)
    return ClientOut.from_orm(updated_client)


def delete_client_profile_photo(user: User) -> ClientOut:
    """
    Remove a foto do Cliente logado, voltando para a foto padrão.
    """
    if user.role != User.UserRole.CLIENT:
        raise PermissionDenied("Apenas clientes podem remover esta foto.")

    client = get_client_by_user_id(user.id)
    if not client:
        raise UserNotFound("Cliente não encontrado.")

    updated_client = remove_client_photo(client=client)
    return ClientOut.from_orm(updated_client)

