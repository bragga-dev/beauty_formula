

import os
from storages.backends.s3boto3 import S3Boto3Storage

class MediaFilesStorage(S3Boto3Storage):
    bucket_name = os.environ.get("MINIO_BUCKET_MEDIA", "beautyformulamedia")
    default_acl = "public-read"
    file_overwrite = False
    custom_domain = (
    f"{os.environ.get('MINIO_PUBLIC_URL')}/"
    f"{os.environ.get('MINIO_BUCKET_MEDIA', 'beautyformulamedia')}")
    url_protocol = os.environ.get("MINIO_URL_PROTOCOL", "http:")

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

