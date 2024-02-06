# -*- coding: utf-8 -*-
# pip install google-cloud-pubsub
# pip install google-auth
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


data = {"camera_id": "000005"}
publish_message(data=data)
