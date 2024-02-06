# -*- coding: utf-8 -*-
import base64
import json
import time
import traceback
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Union

import functions_framework
import pytz
import requests
import sentry_sdk
import vertexai
from google.cloud import bigquery, secretmanager
from langchain.output_parsers import PydanticOutputParser
from pydantic import BaseModel
from vertexai.preview.generative_models import GenerativeModel, Part

PROJECT_ID = "rj-escritorio-dev"
LOCATION = "us-central1"
VERSION_ID = "latest"
DATASET_ID = "vision_ai"
TABLE_ID = "cameras_predicoes"
vertexai.init(project=PROJECT_ID, location=LOCATION)


def get_datetime() -> str:
    timestamp = datetime.now(pytz.timezone("America/Sao_Paulo"))
    return timestamp.strftime("%Y-%m-%dT%H:%M:%S.%f")


class Object(BaseModel):
    object: str
    label_explanation: str
    label: Union[bool, str, None]


class Output(BaseModel):
    objects: List[Object]


class APIVisionAI:
    def __init__(self, username: str, password: str) -> None:
        self.BASE_URL = "https://vision-ai-api-staging-ahcsotxvgq-uc.a.run.app"
        self.username = username
        self.password = password
        self.headers, self.token_renewal_time = self._get_headers()

    def _get_headers(self) -> Tuple[Dict[str, str], float]:
        access_token_response = requests.post(
            f"{self.BASE_URL}/auth/token",
            data={"username": self.username, "password": self.password},
        ).json()
        token = access_token_response["access_token"]
        return {"Authorization": f"Bearer {token}"}, time.time()

    def _refresh_token_if_needed(self) -> None:
        if time.time() - self.token_renewal_time >= 60 * 50:
            self.headers, self.token_renewal_time = self._get_headers()

    def _put(self, path: str) -> requests.Response:
        self._refresh_token_if_needed()
        return requests.put(f"{self.BASE_URL}{path}", headers=self.headers)

    def put_camera_object(
        self, camera_id: str, object_id: str, label_explanation: str, label: str
    ) -> requests.Response:
        return self._put(
            f"/cameras/{camera_id}/objects/{object_id}?label={label}&label_explanation={label_explanation}"  # noqa
        )


def get_secret(secret_id: str) -> str:

    name = f"projects/{PROJECT_ID}/secrets/{secret_id}/versions/{VERSION_ID}"
    client = secretmanager.SecretManagerServiceClient()
    response = client.access_secret_version(request={"name": name})
    return response.payload.data.decode("UTF-8")


def save_data_in_bq(
    json_data: dict,
    error_step: Optional[str] = None,
    ai_response_parsed: Optional[str] = None,
    ai_response: Optional[str] = None,
    error_message: Optional[str] = None,
    error_name: Optional[str] = None,
) -> None:

    client = bigquery.Client()
    table_full_name = f"{PROJECT_ID}.{DATASET_ID}.{TABLE_ID}"

    schema = [
        bigquery.SchemaField("camera_id", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("data_particao", "DATE", mode="NULLABLE"),
        bigquery.SchemaField("start_datetime", "DATETIME", mode="NULLABLE"),
        bigquery.SchemaField("end_datetime", "DATETIME", mode="NULLABLE"),
        bigquery.SchemaField("ai_input", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("ai_response_parsed", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("ai_response", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("error_step", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("error_name", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("error_message", "STRING", mode="NULLABLE"),
    ]

    job_config = bigquery.LoadJobConfig(
        schema=schema,
        # Optionally, set the write disposition. BigQuery appends loaded rows
        # to an existing table by default, but with WRITE_TRUNCATE write
        # disposition it replaces the table with the loaded data.
        write_disposition="WRITE_APPEND",
        time_partitioning=bigquery.TimePartitioning(
            type_=bigquery.TimePartitioningType.DAY,
            field="data_particao",  # name of column to use for partitioning
        ),
    )

    end_datetime = get_datetime()
    json_data["end_datetime"] = end_datetime
    json_data["ai_response_parsed"] = ai_response_parsed
    json_data["ai_response"] = ai_response
    json_data["error_step"] = error_step
    json_data["error_name"] = error_name
    json_data["error_message"] = error_message

    json_data = json.loads(json.dumps([json_data]))
    try:
        job = client.load_table_from_json(json_data, table_full_name, job_config=job_config)
        job.result()
    except Exception:
        raise Exception(json_data)


def get_prediction(
    bq_data_json: dict,
    image_url: str,
    prompt_text: str,
    google_api_model: str,
    max_output_tokens: int,
    temperature: float,
    top_k: int,
    top_p: int,
) -> Dict:

    # llm = ChatGoogleGenerativeAI(
    #     model=google_api_model,
    #     google_api_key=google_api_key,
    #     max_output_token=max_output_tokens,
    #     temperature=temperature,
    #     top_k=top_k,
    #     top_p=top_p,
    #     stream=True,
    # )

    # content = [
    #     {"type": "text", "text": prompt_text},
    #     {"type": "image_url", "image_url": image_url},
    # ]  # noqa

    # message = HumanMessage(content=content)
    # response = llm.invoke([message])
    # ai_response = response.content

    try:

        image_response = requests.get(image_url)
        model = GenerativeModel(google_api_model)
        responses = model.generate_content(
            contents=[prompt_text, Part.from_data(image_response.content, "image/png")],
            generation_config={
                "max_output_tokens": max_output_tokens,
                "temperature": temperature,
                "top_k": top_k,
                "top_p": top_p,
            },
        )

        ai_response = responses.text

    except Exception as exception:

        save_data_in_bq(
            json_data=bq_data_json,
            error_step="ai_request",
            ai_response_parsed=None,
            ai_response=None,
            error_message=str(traceback.format_exc(chain=False)),
            error_name=str(type(exception).__name__),
        )
        raise exception

    output_parser = PydanticOutputParser(pydantic_object=Output)

    try:
        response_parsed = output_parser.parse(ai_response)
    except Exception as exception:
        save_data_in_bq(
            json_data=bq_data_json,
            error_step="ai_response_parser",
            ai_response_parsed=None,
            ai_response=ai_response,
            error_message=str(traceback.format_exc(chain=False)),
            error_name=str(type(exception).__name__),
        )
        raise exception

    return response_parsed.dict()


@functions_framework.cloud_event
def predict(cloud_event: dict) -> None:
    """
    Triggered from a message on a Cloud Pub/Sub topic.
    """
    start_datetime = get_datetime()
    # Decodes and loads the data from the Cloud Event
    data_bytes = base64.b64decode(cloud_event.data["message"]["data"])
    data = json.loads(data_bytes.decode("utf-8"))

    # Get secrets
    vision_ai_secrets_str = get_secret("vision-ai-cloud-function-secrets")
    vision_ai_secrets = json.loads(vision_ai_secrets_str)

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
        bq_data_json=bq_data,
        image_url=data["image_url"],
        prompt_text=data["prompt_text"],
        google_api_model=data["model"],
        max_output_tokens=data["max_output_tokens"],
        temperature=data["temperature"],
        top_k=data["top_k"],
        top_p=data["top_p"],
    )

    retry_count = 5
    while retry_count > 0:
        try:
            vision_ai_api = APIVisionAI(
                username=vision_ai_secrets["vision_ai_api_username"],
                password=vision_ai_secrets["vision_ai_api_password"],
            )

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
                label = str(label).lower()

                if object_id is not None:
                    try:
                        put_response = vision_ai_api.put_camera_object(
                            camera_id=camera_id,
                            object_id=object_id,
                            label_explanation=label_explanation,
                            label=label,
                        )
                        if (
                            put_response.status_code != 200
                        ):  # TODO pensar o que fazer com o label que nao existem, criar ou so ignora? # noqa
                            item["api_error_step"] = "api_object_not_exists"
                            item["api_error_message"] = json.dumps(put_response.json())
                        item["api_status_code"] = put_response.status_code
                    except Exception as exception:
                        item["api_error_step"] = "api_put_object"
                        item["api_error_name"] = type(exception).__name__
                        item["api_error_message"] = traceback.format_exc(chain=False)
                else:
                    item["api_error_step"] = "api_object_id_not_exists"
                ai_response_parsed_bq.append(item)

            save_data_in_bq(
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
                    json_data=bq_data,
                    error_step="api_authentication_error",
                    ai_response_parsed=json.dumps(ai_response_parsed_bq),
                    ai_response=None,
                    error_message=str(traceback.format_exc(chain=False)),
                    error_name=str(type(exception).__name__),
                )

                raise exception
            retry_count += -1
