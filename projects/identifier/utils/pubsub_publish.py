# -*- coding: utf-8 -*-
# pip install google-cloud-pubsub
# pip install google-auth
import base64
import json
from typing import Dict, Optional

from google.auth import jwt
from google.cloud import pubsub_v1
from google.cloud.pubsub_v1.publisher.futures import Future


def get_credential_client(secret_path: str) -> pubsub_v1.PublisherClient:
    service_account_info = json.load(open(secret_path))
    publisher_audience = "https://pubsub.googleapis.com/google.pubsub.v1.Publisher"
    audience = "https://pubsub.googleapis.com/google.pubsub.v1.Subscriber"

    credentials = jwt.Credentials.from_service_account_info(service_account_info, audience=audience)
    credentials_pub = credentials.with_claims(audience=publisher_audience)
    publisher = pubsub_v1.PublisherClient(credentials=credentials_pub)

    return publisher


def publish_message(data: Dict[str, str], secret_path: Optional[str] = None) -> Future:
    if secret_path is not None:
        publisher = get_credential_client(secret_path=secret_path)
    else:
        publisher = pubsub_v1.PublisherClient()

    project_id = "rj-escritorio-dev"
    topic = "vision-ai-deteccao-alagamento"
    topic_name = f"projects/{project_id}/topics/{topic}"

    byte_data = json.dumps(data).encode("utf-8")
    future = publisher.publish(topic_name, byte_data)

    return future.result()


data = {
    "camera_id": "000398",
    "image_url": "str",
    "prompt_text": "str",
    "object_ids": "str",
    "object_slugs": "str",
    "model": "gemini-pro-vision",
    "max_output_tokens": 2000,
    "temperature": 0.1,
    "top_k": 32,
    "top_p": 1,
}


data_b64 = base64.b64encode(json.dumps(data).encode())
data_bytes = base64.b64decode(data_b64)
data = json.loads(data_bytes.decode("utf-8"))

publish_message(data=data)
