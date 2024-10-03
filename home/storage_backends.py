from django.conf import settings
from storages.backends.s3boto3 import S3Boto3Storage
import boto3


class MediaStorage(S3Boto3Storage):
    location = settings.AWS_MEDIA_LOCATION
    file_overwrite = False


def generate_presigned_url(s3_object_key, expiration=3600):
    if not s3_object_key:
        return None

    s3_client = boto3.client(
        "s3",
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name=settings.AWS_STORAGE_REGION,
    )
    s3_object_key = f"{settings.AWS_MEDIA_LOCATION}/{s3_object_key}"
    presigned_url = s3_client.generate_presigned_url(
        "get_object",
        Params={"Bucket": settings.AWS_STORAGE_BUCKET_NAME, "Key": s3_object_key},
        ExpiresIn=expiration,
    )
    return presigned_url
