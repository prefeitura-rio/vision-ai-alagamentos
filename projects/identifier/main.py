# -*- coding: utf-8 -*-
import base64
import io
import json
import time
from typing import List, Union

import functions_framework
import google.generativeai as genai
import requests
import sentry_sdk
from google.cloud import secretmanager
from langchain.output_parsers import PydanticOutputParser

# from langchain_core.messages import HumanMessage
# from langchain_google_genai import ChatGoogleGenerativeAI
from PIL import Image
from pydantic import BaseModel, Field


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


def get_exception(response_ai, data):
    raise Exception(response_ai, data)


def get_prediction(
    data: dict,
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
    # response_ai = response.content

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
    response_ai = responses.text

    output_parser = PydanticOutputParser(pydantic_object=Output)

    try:
        response_parsed = output_parser.parse(response_ai)
    except Exception:
        get_exception(response_ai, data)

    return response_parsed.dict()


@functions_framework.cloud_event
def predict(cloud_event: dict) -> None:
    """
    Triggered from a message on a Cloud Pub/Sub topic.
    """
    # Decodes and loads the data from the Cloud Event
    data_bytes = base64.b64decode(cloud_event.data["message"]["data"])
    data = json.loads(data_bytes.decode("utf-8"))

    # Get secrets
    vision_ai_secrets_str = get_secret("vision-ai-cloud-function-secrets")
    vision_ai_secrets = json.loads(vision_ai_secrets_str)

    sentry_sdk.init(vision_ai_secrets["sentry_dns"])

    # Initializes the Vision AI API client

    # Generates a prediction using the Google Generative AI model
    ai_response_parsed = get_prediction(
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

    camera_id = data.get("camera_id")
    camera_objects_from_api = dict(zip(data["object_slugs"], data["object_ids"]))
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

            if (
                r.status_code != 200
            ):  # TODO pensar o que fazer com o label que nao existem, criar ou so ignora?
                # raise Exception(f"Error: {r.status_code}\n{r}")
                print(camera_id)
                print(item["object"], ": ", item["label"])
                print(f"Error: {r.status_code}\n{r.json()}\n\n")
            # else:
            #     print(camera_id)
            #     print(f"{r.json()}\n\n")
