# -*- coding: utf-8 -*-
import base64
import io
import json
from typing import Any, Callable, Dict, List
from uuid import uuid4

from app import config
from google.cloud import storage
from google.cloud.storage.blob import Blob
from google.oauth2 import service_account
from PIL import Image
from pydantic import BaseModel
from tortoise.models import Model


def apply_to_list(lst: List[Any], fn: Callable) -> List[Any]:
    """
    Applies a function to a whole list and returns the result.
    """
    return [fn(item) for item in lst]


def download_camera_snapshot_from_bucket(*, camera_id: str) -> str:
    """
    Downloads a camera snapshot from the bucket.
    Mode needs to be "prod" or "staging"

    Args:
        camera_id (str): The camera id.

    Returns:
        str: The base64 encoded image.
    """
    # Set blob path
    blob_path = generate_blob_path(camera_id)
    # Download file
    tmp_fname = f"/tmp/{uuid4()}.png"
    download_file_from_bucket(
        bucket_name=config.GCS_BUCKET_NAME,
        source_blob_name=blob_path,
        destination_file_name=tmp_fname,
    )
    # Read file
    with open(tmp_fname, "rb") as f:
        image_base64 = base64.b64encode(f.read()).decode("utf-8")
    return image_base64


def download_file_from_bucket(
    bucket_name: str, source_blob_name: str, destination_file_name: str
) -> None:
    """
    Downloads a file from the bucket.
    Mode needs to be "prod" or "staging"

    Args:
        bucket_name (str): The name of the bucket.
        source_blob_name (str): The name of the blob.
        destination_file_name (str): The path of the file to download to.

    Returns:
        None
    """
    storage_client = get_gcs_client()
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(source_blob_name)
    blob.download_to_filename(destination_file_name)


def generate_blob_path(camera_id: str) -> str:
    """
    Generates a blob path for a camera snapshot.

    Args:
        camera_id (str): The camera id.

    Returns:
        str: The blob path.
    """
    return f"{config.GCS_BUCKET_PATH_PREFIX}/{camera_id}.png"


def get_gcp_credentials(
    scopes: List[str] = None,
) -> service_account.Credentials:
    """
    Gets credentials from env vars
    """
    env: str = config.GCP_SERVICE_ACCOUNT_CREDENTIALS
    if not env:
        raise ValueError("GCP_SERVICE_ACCOUNT_CREDENTIALS env var not set!")
    info: dict = json.loads(base64.b64decode(env))
    cred: service_account.Credentials = (
        service_account.Credentials.from_service_account_info(info)
    )
    if scopes:
        cred = cred.with_scopes(scopes)
    return cred


def get_gcs_client() -> storage.Client:
    """
    Get a GCS client with the credentials from the environment.
    Mode needs to be "prod" or "staging"

    Args:
        mode (str): The mode to filter by (prod or staging).

    Returns:
        storage.Client: The GCS client.
    """
    credentials = get_gcp_credentials()
    return storage.Client(credentials=credentials)


def slugify(text: str) -> str:
    """
    Slugifies a string.

    Args:
        text (str): The string to slugify.

    Returns:
        str: The slugified string.
    """
    return text.lower().replace(" ", "-").replace("_", "-").replace(".", "-").strip()


def transform_tortoise_to_pydantic(
    tortoise_model: Model, pydantic_model: BaseModel, vars_map: Dict[str, str]
) -> BaseModel:
    """
    Transform a Tortoise ORM model to a Pydantic model using a variable mapping.

    Args:
        tortoise_model (Model): The Tortoise ORM model to transform.
        pydantic_model (BaseModel): The Pydantic model to transform into.
        vars_map (Dict[str, str]): A dictionary mapping Tortoise ORM variable names
                                   to Pydantic variable names.

    Returns:
        BaseModel: An instance of the Pydantic model with values from the Tortoise model.
    """
    # Create a dictionary to store Pydantic field values
    pydantic_values = {}

    # Iterate through the variable mapping
    for tortoise_var, pydantic_var in vars_map.items():
        # Get the value from the Tortoise model
        tortoise_value = getattr(tortoise_model, tortoise_var, None)

        # Set the value in the Pydantic dictionary
        pydantic_values[pydantic_var] = tortoise_value

    # Create an instance of the Pydantic model with the transformed values
    transformed_pydantic_model = pydantic_model(**pydantic_values)

    return transformed_pydantic_model


def upload_camera_snapshot_to_bucket(*, image_base64: str, camera_id: str) -> str:
    """
    Uploads a camera snapshot to the bucket.
    Mode needs to be "prod" or "staging"

    Args:
        image_base64 (str): The base64 encoded image.
        camera_id (str): The camera id.

    Returns:
        str: The public URL of the uploaded image.
    """
    # Save image to temp file
    tmp_fname = f"/tmp/{uuid4()}.png"
    img = Image.open(io.BytesIO(base64.b64decode(image_base64)))
    with open(tmp_fname, "wb") as f:
        img.save(f, format="PNG")
    # Set blob path
    blob_path = generate_blob_path(camera_id)
    blob = upload_file_to_bucket(
        bucket_name=config.GCS_BUCKET_NAME,
        file_path=tmp_fname,
        destination_blob_name=blob_path,
    )
    # Return public URL
    return blob.public_url


def upload_file_to_bucket(
    bucket_name: str, file_path: str, destination_blob_name: str
) -> "Blob":
    """
    Uploads a file to the bucket.
    Mode needs to be "prod" or "staging"

    Args:
        bucket_name (str): The name of the bucket.
        file_path (str): The path of the file to upload.
        destination_blob_name (str): The name of the blob.

    Returns:
        Blob: The uploaded blob.
    """
    storage_client = get_gcs_client()
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(destination_blob_name)
    blob.upload_from_filename(file_path)
    return blob
