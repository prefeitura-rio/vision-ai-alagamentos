# -*- coding: utf-8 -*-
import base64
import json
import time

import functions_framework
import requests
from google.cloud import secretmanager
from langchain_core.messages import HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI


class APIVisionAI:
    def __init__(self, username: str, password: str, client_id: str, client_secret: str):
        self.BASE_URL = "https://vision-ai-api-staging-ahcsotxvgq-uc.a.run.app"
        self.username = username
        self.password = password
        self.client_id = client_id
        self.client_secret = client_secret
        self.token: str
        self.token_renewal_time: float
        self.token, self.token_renewal_time = self._get_token()

    def _get_token(self) -> tuple[str, float]:
        # Obtains and returns an access token along with the time of token retrieval
        access_token_response = requests.post(
            "https://authentik.dados.rio/application/o/token/",
            data={
                "grant_type": "password",
                "username": self.username,
                "password": self.password,
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "scope": "profile",
            },
        ).json()
        return access_token_response["access_token"], time.time()

    def _refresh_token_if_needed(self) -> None:
        # Refreshes the token if it has expired
        if time.time() - self.token_renewal_time >= 60:
            self.token, self.token_renewal_time = self._get_token()

    def _get(self, path: str) -> dict:
        # Performs a GET request with a refreshed token
        self._refresh_token_if_needed()
        response = requests.get(
            f"{self.BASE_URL}{path}", headers={"Authorization": f"Bearer {self.token}"}
        )
        return response.json()

    def _put(self, path: str, json_data: dict = None) -> dict:
        # Performs a PUT request with a refreshed token
        self._refresh_token_if_needed()
        response = requests.put(
            f"{self.BASE_URL}{path}",
            json=json_data,
            headers={"Authorization": f"Bearer {self.token}"},
        )
        return response.json()

    def _post(self, path: str, json_data: dict = None) -> dict:
        # Performs a POST request with a refreshed token
        self._refresh_token_if_needed()
        response = requests.post(
            f"{self.BASE_URL}{path}",
            json=json_data,
            headers={"Authorization": f"Bearer {self.token}"},
        )
        return response.json()

    def get_prompt(self) -> dict:
        # Retrieves a prompt from the Vision AI API
        return self._get("/prompts?page=1&size=100").get("items")[0]

    def get_snapshot(self, camera_id: str) -> str:
        # Retrieves a snapshot image in base64 format from the Vision AI API
        return self._get(f"/cameras/{camera_id}/snapshot")["image_base64"]

    def get_object_id(self, name: str) -> str:
        # Retrieves the object ID based on the object name from the Vision AI API
        return self._get(f"/objects?name={name}")["items"][0]["id"]

    def put_camera_object_details(self, camera_id: str, object_id: str, label: str) -> dict:
        # Updates camera object details using a PUT request
        return self._put(
            path=f"/cameras/{camera_id}/objects/{object_id}?label={str(label).lower()}",
            json_data={"label": label},
        )

    def get_camera_object_details(self, camera_id: str, object_id: str) -> dict:
        # Retrieves camera object details using a GET request
        return self._get(path=f"/cameras/{camera_id}/objects/{object_id}")

    def post_camera_object(self, camera_id: str, object_id: str) -> dict:
        # Creates a new camera object using a POST request
        return self._post(path=f"/cameras/{camera_id}/objects?object_id={object_id}")


def get_secret(secret_id: str) -> str:
    # Retrieves a secret from Google Cloud Secret Manager
    project_id = "rj-escritorio-dev"
    version_id = "latest"
    name = f"projects/{project_id}/secrets/{secret_id}/versions/{version_id}"
    client = secretmanager.SecretManagerServiceClient()
    response = client.access_secret_version(request={"name": name})
    secret = response.payload.data.decode("UTF-8")
    return secret


def get_content(prompt_text: str, image_base64: str) -> list[dict]:
    # Constructs and returns content for the prediction request
    return [
        {"type": "text", "text": prompt_text},
        {"type": "image_url", "image_url": "data:image/png;base64," + image_base64},
    ]


def get_prediction(
    image_base64: str,
    prompt_text: str,
    google_api_key: str,
    google_api_model: str = "gemini-pro-vision",
    max_output_tokens: int = 300,
    temperature: float = 0.4,
    top_k: int = 32,
    top_p: int = 1,
) -> dict:
    # Retrieves a prediction using the Google Generative AI model
    llm = ChatGoogleGenerativeAI(
        model=google_api_model,
        google_api_key=google_api_key,
        max_output_token=max_output_tokens,
        temperature=temperature,
        top_k=top_k,
        top_p=top_p,
    )
    content = get_content(prompt_text=prompt_text, image_base64=image_base64)

    message = HumanMessage(content=content)
    response = llm.invoke([message])
    json_string = response.content.replace("```json\n", "").replace("\n```", "").replace("'", '"')
    return json.loads(json_string)


@functions_framework.cloud_event
def predict(cloud_event: dict) -> None:
    """
    Triggered from a message on a Cloud Pub/Sub topic.
    """
    # Decodes and loads the data from the Cloud Event
    data_bytes = base64.b64decode(cloud_event.data["message"]["data"])
    data = json.loads(data_bytes.decode("utf-8"))

    # Extracts relevant information from the Cloud Event data
    camera_id = data.get("camera_id")
    google_api_key = get_secret("gemini-api-key-cloud-functions")
    vision_ai_api_secrets = get_secret("vision-ai-api-secrets-cloud-functions")
    vision_ai_api_secrets = json.loads(vision_ai_api_secrets)

    # Initializes the Vision AI API client
    vision_ai_api = APIVisionAI(
        username=vision_ai_api_secrets["username"],
        password=vision_ai_api_secrets["password"],
        client_id=vision_ai_api_secrets["client_id"],
        client_secret=vision_ai_api_secrets["client_secret"],
    )

    # Obtains a snapshot image in base64 format from the Vision AI API
    image_base64 = vision_ai_api.get_snapshot(camera_id=camera_id)

    # Retrieves prompt parameters from the Vision AI API
    prompt_parameters = vision_ai_api.get_prompt()

    # Generates a prediction using the Google Generative AI model
    label = get_prediction(
        image_base64=image_base64,
        prompt_text=prompt_parameters.get("prompt_text"),
        google_api_key=google_api_key,
        google_api_model="gemini-pro-vision",
        max_output_tokens=prompt_parameters.get("max_output_tokens"),
        temperature=prompt_parameters.get("temperature"),
        top_k=prompt_parameters.get("top_k"),
        top_p=prompt_parameters.get("top_p"),
    )

    # Obtains the object ID for "alagamento"
    object_id = vision_ai_api.get_object_id(name="alagamento")

    # Retrieves camera object details
    camera_object_detail = vision_ai_api.get_camera_object_details(
        camera_id=camera_id,
        object_id=object_id,
    )

    # If the label is not present in camera object details, create a new camera object
    if "label" not in camera_object_detail:
        vision_ai_api.post_camera_object(
            camera_id=camera_id,
            object_id=object_id,
        )

    # Updates camera object details with the predicted label
    put_response = vision_ai_api.put_camera_object_details(
        camera_id=camera_id, object_id=object_id, label=label["label"]
    )

    # Prints the response from updating camera object details
    print(put_response)
