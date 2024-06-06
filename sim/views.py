import logging
import tempfile

import boto3
from botocore.exceptions import ClientError
from django.shortcuts import render
from django.conf import settings


ACCEPTED_FILE_TYPES = (".jpg", ".jpeg", ".png")


def generate_presigned_post(
    bucket_name: str, filename: str, expiration: int = 600
) -> dict:
    s3_client = boto3.client(
        "s3",
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
    )
    return s3_client.generate_presigned_post(
        Bucket=bucket_name,
        Key=filename,
        ExpiresIn=expiration,
    )


def create_presigned_url(
    bucket_name: str, object_name: str, expiration: int = 3600
) -> str:
    # Generate a presigned URL for the S3 object
    s3_client = boto3.client(
        "s3",
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
    )

    try:
        response = s3_client.generate_presigned_url(
            "get_object",
            Params={"Bucket": bucket_name, "Key": object_name},
            ExpiresIn=expiration,
        )
    except ClientError as e:
        logging.error(e)
        return None

    # The response contains the presigned URL
    return response


def get_image_urls() -> list[str] | None:
    s3_client = boto3.client(
        "s3",
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
    )

    response = s3_client.list_objects_v2(Bucket=settings.AWS_BUCKET_NAME)

    if response.get("Contents"):
        object_names = [
            content["Key"]
            for content in response["Contents"]
            if content["Key"].lower().endswith(ACCEPTED_FILE_TYPES)
        ]

        return [
            create_presigned_url(
                bucket_name=settings.AWS_BUCKET_NAME, object_name=object_name
            )
            for object_name in object_names
        ]
    else:
        return []


def uploader(request):
    """
    We render the page with or without data for a presigned post upload.
    """

    image_urls = get_image_urls()
    context = {"image_urls": image_urls}

    if request.method == "POST":
        file = request.FILES["file"]
        name = file.name
        content_type = file.content_type

        # Add any Django form validation here to check the file is valid, correct size, type, etc.

        bucket_name = settings.AWS_BUCKET_NAME
        presigned_data = generate_presigned_post(bucket_name, name)

        context["url"] = presigned_data["url"]
        context["fields"] = presigned_data["fields"]
        context["path"] = f"to {bucket_name}/{name}"
        print(f"{context = }")
        return render(request, "uploader.html", context)

    return render(request, "uploader.html", context)


def conventional_uploader(request):

    if request.method == "POST":
        file = request.FILES["file"]
        name = file.name
        content_type = file.content_type

        # Add any Django form validation here to check the file is valid, correct size, type, etc.

        with tempfile.NamedTemporaryFile() as tmp_file:
            for chunk in file.chunks():
                tmp_file.write(chunk)

            tmp_file.flush()

            s3 = boto3.client(
                "s3",
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            )
            s3.upload_file(tmp_file.name, settings.AWS_BUCKET_NAME, file.name)

    image_urls = get_image_urls()
    context = {"image_urls": image_urls}

    return render(request, "conventional_uploader.html", context)
