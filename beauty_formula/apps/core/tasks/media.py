"""
Tasks Celery — limpeza de arquivos de mídia (MinIO/S3).

Deletar um arquivo antigo no MinIO é uma chamada de rede síncrona (DELETE)
que não precisa bloquear a resposta da API: o usuário só precisa do arquivo
NOVO já salvo para receber a `photo_url`/`image_url` atualizada. A remoção
do arquivo antigo é side-effect de limpeza e roda em background aqui.
"""
import logging

from celery import shared_task
from django.core.files.storage import default_storage

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=30,
)
def delete_old_media_file(self, file_name: str) -> None:
    """
    Remove um arquivo do storage padrão (MediaFilesStorage/MinIO) pelo nome/key.

    Silenciosamente ignora arquivos que já não existem (idempotente).
    """
    if not file_name:
        return
    try:
        if default_storage.exists(file_name):
            default_storage.delete(file_name)
    except Exception as exc:
        logger.warning("Falha ao deletar arquivo antigo '%s' do storage: %s", file_name, exc)
        raise self.retry(exc=exc)