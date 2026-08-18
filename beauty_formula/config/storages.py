import os
from django.conf import settings
from storages.backends.s3boto3 import S3Boto3Storage

# ─────────────────────────────────────────────────────────────────────────
# `url_protocol` lia `MINIO_URL_PROTOCOL` direto de `os.environ` — mas
# quem o desenvolvedor de fato configura é o Django settings
# (`prod.py` seta `MINIO_URL_PROTOCOL = "https:"`, `dev.py` seta
# `"http:"`). Sem essa MESMA chave também definida como variável de
# ambiente do sistema (fora do .env do Django), `os.environ.get` caía
# sempre no default `"http:"` — inclusive em produção. Imagens servidas
# por http (não https) são bloqueadas silenciosamente por vários
# clientes de e-mail (Gmail, Outlook), o que explica fotos que aparecem
# em alguns e-mails e não em outros. Lendo de `settings` em vez de
# `os.environ`, o valor que o dev configurou em prod.py/dev.py passa a
# valer de verdade.
# ─────────────────────────────────────────────────────────────────────────

class MediaFilesStorage(S3Boto3Storage):
    bucket_name = os.environ.get("MINIO_BUCKET_MEDIA", "beautyformulamedia")
    default_acl = "public-read"
    file_overwrite = True
    custom_domain = (
    f"{os.environ.get('MINIO_PUBLIC_URL')}/"
    f"{os.environ.get('MINIO_BUCKET_MEDIA', 'beautyformulamedia')}")
    url_protocol = getattr(settings, "MINIO_URL_PROTOCOL", os.environ.get("MINIO_URL_PROTOCOL", "http:"))

class StaticFilesStorage(S3Boto3Storage):
    bucket_name = os.environ.get("MINIO_BUCKET_STATIC", "beautyformulastatic")
    default_acl = "public-read"
    file_overwrite = True

class PrivateFilesStorage(S3Boto3Storage):
    bucket_name = os.environ.get("MINIO_BUCKET_PRIVATE", "beautyformulaprivate")
    default_acl = None        
    file_overwrite = False
    querystring_auth = True   
    querystring_expire = 300