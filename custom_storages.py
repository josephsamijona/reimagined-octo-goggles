# custom_storages.py
from storages.backends.s3boto3 import S3Boto3Storage
from django.conf import settings

class MediaStorage(S3Boto3Storage):
    """
    Default storage for general media files.
    Maps to 'jhbridge-documents-prod' for compatibility with migrated data.
    Location 'media' matches the B2 structure.
    """
    bucket_name = 'jhbridge-documents-prod'
    location = 'media'

class DocumentStorage(S3Boto3Storage):
    """
    Storage for general documents.
    """
    bucket_name = 'jhbridge-documents-prod'
    location = 'media'

class ContractStorage(S3Boto3Storage):
    """
    Secure storage for signed contracts (Versioning enabled).
    """
    bucket_name = 'jhbridge-contracts-prod'
    location = ''
    file_overwrite = False

class SignatureStorage(S3Boto3Storage):
    """
    Storage for signature images.
    """
    bucket_name = 'jhbridge-signatures-prod'
    location = ''

class AssetStorage(S3Boto3Storage):
    """
    Storage for public assets (images, static resources).
    Use root location because assets were migrated to root of jhbridge-assets.
    """
    bucket_name = 'jhbridge-assets'
    location = ''
    querystring_auth = False

class TempStorage(S3Boto3Storage):
    """
    Storage for temporary uploads (Lifecycle 24h).
    """
    bucket_name = 'jhbridge-temp-uploads'
    location = ''