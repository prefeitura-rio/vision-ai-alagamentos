# -*- coding: utf-8 -*-
import base64
import json
import traceback
from os import getenv

import functions_framework
import requests
import sentry_sdk
import vertexai
from google.cloud import secretmanager
from vertexai.preview import generative_models
from vision_ai.base.api import VisionaiAPI
from vision_ai.base.cloudfunctions.bq import save_data_in_bq
from vision_ai.base.cloudfunctions.predict import get_prediction
from vision_ai.base.utils import get_datetime

PROJECT_ID = getenv("GCP_PROJECT_ID")
LOCATION = "us-central1"
VERSION_ID = "latest"
DATASET_ID = "vision_ai"
TABLE_ID = "cameras_predicoes"
vertexai.init(project=PROJECT_ID, location=LOCATION)

SAFETY_CONFIG = {
    generative_models.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: generative_models.HarmBlockThreshold.BLOCK_NONE,
    generative_models.HarmCategory.HARM_CATEGORY_HARASSMENT: generative_models.HarmBlockThreshold.BLOCK_NONE,
    generative_models.HarmCategory.HARM_CATEGORY_HATE_SPEECH: generative_models.HarmBlockThreshold.BLOCK_NONE,
    generative_models.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: generative_models.HarmBlockThreshold.BLOCK_NONE,
}


class APIVisionAI(VisionaiAPI):
    def post_identification(
        self, camera_id: str, snapshot_id: str, object_id: str, label_explanation: str, label: str
    ) -> requests.Response:
        return self._post(
            f"/cameras/{camera_id}/snapshots/{snapshot_id}/identifications?object_id={object_id}&label_value={label}&label_explanation={label_explanation}"  # noqa
        )


def get_secret(secret_id: str) -> str:
    name = f"projects/{PROJECT_ID}/secrets/{secret_id}/versions/{VERSION_ID}"
    client = secretmanager.SecretManagerServiceClient()
    response = client.access_secret_version(request={"name": name})
    return response.payload.data.decode("UTF-8")


# Get secrets
vision_ai_secrets_str = get_secret("vision-ai-cloud-function-secrets")
vision_ai_secrets = json.loads(vision_ai_secrets_str)
vision_ai_api = APIVisionAI(
    username=vision_ai_secrets["vision_ai_api_username"],
    password=vision_ai_secrets["vision_ai_api_password"],
)


@functions_framework.cloud_event
def predict(cloud_event: dict) -> None:
    """
    Triggered from a message on a Cloud Pub/Sub topic
    """
    start_datetime = get_datetime()
    # Decodes and loads the data from the Cloud Event.
    data_bytes = base64.b64decode(cloud_event.data["message"]["data"])
    data = json.loads(data_bytes.decode("utf-8"))

    sentry_sdk.init(vision_ai_secrets["sentry_dns"])
    camera_id = data.get("camera_id")
    data.pop("camera_id")
    bq_data = {
        "camera_id": camera_id,
        "data_particao": start_datetime[:10],
        "start_datetime": start_datetime,
        "end_datetime": None,
        "ai_input": json.dumps(data),
        "ai_response_parsed": None,
        "ai_response": None,
        "error_step": None,
        "error_name": None,
        "error_message": None,
    }

    # Generates a prediction using the Google Generative AI model
    ai_response_parsed = get_prediction(
        project_id=PROJECT_ID,
        dataset_id=DATASET_ID,
        table_id=TABLE_ID,
        bq_data_json=bq_data,
        image_url=data["image_url"],
        prompt_text=data["prompt_text"],
        google_api_model=data["model"],
        max_output_tokens=data["max_output_tokens"],
        temperature=data["temperature"],
        top_k=data["top_k"],
        top_p=data["top_p"],
        safety_settings=SAFETY_CONFIG,
    )

    retry_count = 5
    while retry_count > 0:
        try:
            vision_ai_api.refresh_token()
            camera_objects_from_api = dict(zip(data["object_slugs"], data["object_ids"]))
            ai_response_parsed_bq = []
            for item in ai_response_parsed["objects"]:
                item["api_status_code"] = None
                item["api_error_step"] = None
                item["api_error_name"] = None
                item["api_error_message"] = None

                object_id = camera_objects_from_api.get(item["object"], None)
                label_explanation = item["label_explanation"]
                label = item["label"]
                label = label if label is not None else "null"
                label = str(label).lower()
                item["label"] = label
                if object_id is not None:
                    try:
                        post_response = vision_ai_api.post_identification(
                            camera_id=camera_id,
                            snapshot_id=data["snapshot_id"],
                            object_id=object_id,
                            label_explanation=label_explanation,
                            label=label,
                        )
                        if (
                            post_response.status_code != 200
                        ):  # TODO pensar o que fazer com o label que nao existem, criar ou so ignora? # noqa
                            item["api_error_step"] = "api_object_not_exists"
                            item["api_error_message"] = json.dumps(post_response.json())
                        item["api_status_code"] = post_response.status_code
                    except Exception as exception:
                        item["api_error_step"] = "api_post_object"
                        item["api_error_name"] = type(exception).__name__
                        item["api_error_message"] = traceback.format_exc(chain=False)
                else:
                    item["api_error_step"] = "api_object_id_not_exists"
                ai_response_parsed_bq.append(item)

            save_data_in_bq(
                project_id=PROJECT_ID,
                dataset_id=DATASET_ID,
                table_id=TABLE_ID,
                json_data=bq_data,
                error_step=None,
                ai_response_parsed=json.dumps(ai_response_parsed_bq),
                ai_response=None,
                error_message=None,
                error_name=None,
            )
            retry_count = 0
        except Exception as exception:
            if retry_count == 0:
                ai_response_parsed_bq = []
                for item in ai_response_parsed["objects"]:
                    item["api_status_code"] = None
                    item["api_error_step"] = None
                    item["api_error_name"] = None
                    item["api_error_message"] = None
                    ai_response_parsed_bq.append(item)

                save_data_in_bq(
                    project_id=PROJECT_ID,
                    dataset_id=DATASET_ID,
                    table_id=TABLE_ID,
                    json_data=bq_data,
                    error_step="api_authentication_error",
                    ai_response_parsed=json.dumps(ai_response_parsed_bq),
                    ai_response=None,
                    error_message=str(traceback.format_exc(chain=False)),
                    error_name=str(type(exception).__name__),
                )

                raise exception
            retry_count += -1
