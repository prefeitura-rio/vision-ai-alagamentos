# -*- coding: utf-8 -*-
import base64
import io
import json
import time
import traceback
from datetime import datetime
from typing import List, Union

import functions_framework
import google.generativeai as genai
import pytz
import requests
import sentry_sdk
from google.cloud import bigquery, secretmanager
from langchain.output_parsers import PydanticOutputParser

# from langchain_core.messages import HumanMessage
# from langchain_google_genai import ChatGoogleGenerativeAI
from PIL import Image
from pydantic import BaseModel, Field


def get_datetime():
    timestamp = datetime.now(pytz.timezone("America/Sao_Paulo"))
    return timestamp.strftime("%Y-%m-%dT%H:%M:%S.%f")


class Object(BaseModel):
    object: str = Field(description="The object from the objects table")
    label_explanation: str = Field(
        description="Highly detailed visual description of the image given the object context"
    )
    label: Union[bool, str, None] = Field(
        description="Label indicating the condition or characteristic of the object"
    )


class Output(BaseModel):
    objects: List[Object]


class APIVisionAI:
    def __init__(self, username, password):
        self.BASE_URL = "https://vision-ai-api-staging-ahcsotxvgq-uc.a.run.app"
        self.username = username
        self.password = password
        self.headers, self.token_renewal_time = self._get_headers()

    def _get_headers(self):
        access_token_response = requests.post(
            f"{self.BASE_URL}/auth/token",
            data={
                "username": self.username,
                "password": self.password,
            },
        ).json()
        token = access_token_response["access_token"]
        return {"Authorization": f"Bearer {token}"}, time.time()

    def _refresh_token_if_needed(self):
        if time.time() - self.token_renewal_time >= 120:
            self.header, self.token_renewal_time = self._get_headers()

    def _get(self, path):
        self._refresh_token_if_needed()
        response = requests.get(f"{self.BASE_URL}{path}", headers=self.headers)
        return response.json()

    def _put(self, path):
        self._refresh_token_if_needed()
        response = requests.put(
            f"{self.BASE_URL}{path}",
            headers=self.headers,
        )
        return response

    def _post(self, path):
        self._refresh_token_if_needed()
        response = requests.post(
            f"{self.BASE_URL}{path}",
            headers=self.headers,
        )
        return response.json()

    def put_camera_object(self, camera_id, object_id, label_explanation, label):
        return self._put(
            path=f"/cameras/{camera_id}/objects/{object_id}?label={label}&label_explanation={label_explanation}",  # noqa
        )


def get_secret(secret_id: str) -> str:
    # Retrieves a secret from Google Cloud Secret Manager
    project_id = "rj-escritorio-dev"
    version_id = "latest"
    name = f"projects/{project_id}/secrets/{secret_id}/versions/{version_id}"
    client = secretmanager.SecretManagerServiceClient()
    response = client.access_secret_version(request={"name": name})
    secret = response.payload.data.decode("UTF-8")
    return secret


def get_exception(ai_response, data):
    raise Exception(ai_response, data)


def save_data_in_bq(
    json_data: dict,
    error_step=None,
    ai_response_parsed=None,
    ai_response=None,
    error_message=None,
    error_name=None,
):
    project_id = "rj-escritorio-dev"
    dataset_id = "vision_ai"
    table_id = "cameras_predicoes"
    client = bigquery.Client()
    table_full_name = f"{project_id}.{dataset_id}.{table_id}"

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

    json_data = json.loads(json.dumps(json_data))
    job = client.load_table_from_json(json_data, table_full_name, job_config=job_config)
    job.result()


def get_prediction(
    bq_data_json: dict,
    image_url: str,
    prompt_text: str,
    google_api_key: str,
    google_api_model: str,
    max_output_tokens: int,
    temperature: float,
    top_k: int,
    top_p: int,
) -> dict:

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
        image = Image.open(io.BytesIO(image_response.content))
        genai.configure(api_key=google_api_key)
        model = genai.GenerativeModel(google_api_model)
        responses = model.generate_content(
            contents=[prompt_text, image],
            generation_config={
                "max_output_tokens": max_output_tokens,
                "temperature": temperature,
                "top_k": top_k,
                "top_p": top_p,
            },
            stream=True,
        )

        responses.resolve()
        ai_response = responses.text
    except Exception as exception:
        save_data_in_bq(
            json_data=bq_data_json,
            error_step="ai_request",
            ai_response_parsed=None,
            ai_response=None,
            error_message=traceback.format_exc(),
            error_name=type(exception).__name__,
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
            error_message=traceback.format_exc(),
            error_name=type(exception).__name__,
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
        data=data,
        image_url=data["image_url"],
        prompt_text=data["prompt_text"],
        google_api_key=vision_ai_secrets["google_gemini_api_key"],
        google_api_model=data["model"],
        max_output_tokens=data["max_output_tokens"],
        temperature=data["temperature"],
        top_k=data["top_k"],
        top_p=data["top_p"],
    )

    vision_ai_api = APIVisionAI(
        username=vision_ai_secrets["vision_ai_api_username"],
        password=vision_ai_secrets["vision_ai_api_password"],
    )

    camera_objects_from_api = dict(zip(data["object_slugs"], data["object_ids"]))
    ai_response_parsed_bq = []
    for item in ai_response_parsed["objects"]:

        object_id = camera_objects_from_api.get(item["object"], None)
        label_explanation = item["label_explanation"]
        label = item["label"]
        label = str(label).lower()
        if object_id is not None:
            r = vision_ai_api.put_camera_object(
                camera_id=camera_id,
                object_id=object_id,
                label_explanation=label_explanation,
                label=label,
            )

            item["api_error"] = None
            item["api_status_code"] = r.status_code

            if (
                r.status_code != 200
            ):  # TODO pensar o que fazer com o label que nao existem, criar ou so ignora?
                item["api_error"] = r.json()
            ai_response_parsed_bq.append(item)

    save_data_in_bq(
        json_data=bq_data,
        error_step=None,
        ai_response_parsed=ai_response_parsed_bq,
        ai_response=None,
        error_message=None,
        error_name=None,
    )
