import json
import os
import logging

import boto3
from botocore.exceptions import ClientError
import requests


logger = logging.getLogger(__name__)


def lambda_handler(event: dict, context: object) -> dict:
    bucket_name = event["Records"][0]["s3"]["bucket"]["name"]
    object_key = event["Records"][0]["s3"]["object"]["key"]

    # Initialize the AWS Rekognition client
    rekognition_client = boto3.client("rekognition")

    try:
        # Call the detect_moderation_labels API
        logging.info(
            f"Running the moderation labels operation on {bucket_name}/{object_key}"
        )
        response = rekognition_client.detect_moderation_labels(
            Image={"S3Object": {"Bucket": bucket_name, "Name": object_key}},
            MinConfidence=80,
        )
    except ClientError as client_err:
        error_message = (
            "Couldn't analyze image: " + client_err.response["Error"]["Message"]
        )
        logger.error(f"Error function {context.invoked_function_arn}: {error_message}")

        return {
            "statusCode": 400,
            "body": {
                "Error": client_err.response["Error"]["Code"],
                "ErrorMessage": error_message,
            },
        }

    # Check if the image is labeled inappropriate
    moderation_labels = response.get("ModerationLabels")
    if moderation_labels:
        label_names = [label["Name"] for label in moderation_labels]

        # Delete the inappropriate image from the S3 bucket
        logging.info(f"The object {object_key} is flagged as {label_names}.")
        s3_client = boto3.client("s3")
        s3_client.delete_object(Bucket=bucket_name, Key=object_key)

        # Send a POST request to the specified endpoint
        payload = {
            "bucket": bucket_name,
            "key": object_key,
            "labels": label_names,
        }

        # response = requests.post(
        #     os.getenv("ENDPOINT_URL"),
        #     json=payload,
        # )

        sns_client = boto3.client("sns")
        sns_client.publish(
            TopicArn=os.getenv("MODERATION_NOTIFICATION_TOPIC_ARN"),
            Message=json.dumps(payload),
            MessageStructure="string",
        )

    return {
        "statusCode": 200,
        "body": json.dumps("Lambda function execution completed successfully"),
    }
