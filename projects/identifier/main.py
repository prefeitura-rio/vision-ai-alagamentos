import base64
import io
import json

import functions_framework
from PIL import Image
import google.generativeai as genai
from google.cloud import secretmanager



def get_secret():
    project_id = 'rj-escritorio-dev' 
    secret_id = 'gemini-api-key-cloud-functions'
    version_id = 'latest'  

    name = f"projects/{project_id}/secrets/{secret_id}/versions/{version_id}"

    client = secretmanager.SecretManagerServiceClient()

    response = client.access_secret_version(request={"name": name})

    secret_key = response.payload.data.decode("UTF-8")

    return secret_key

def get_prediction(
    image_base64: str,
    prompt: str,
    google_api_key:str,
    google_api_model:str="gemini-pro-vision",
    max_output_tokens: int = 300,
    temperature: float = 0.4,
    top_k: int = 32,
    top_p: int = 1,
    
):
    img = Image.open(io.BytesIO(base64.b64decode(image_base64)))
    genai.configure(api_key=google_api_key)
    model = genai.GenerativeModel(google_api_model)
    responses = model.generate_content(
        contents=[prompt, img],
        generation_config={
            "max_output_tokens": max_output_tokens,
            "temperature": temperature,
            "top_k": top_k,
            "top_p": top_p,
        },
        stream=True,
    )

    responses.resolve()
    json_string = responses.text.replace("```json\n", "").replace("\n```", "").replace("'", '"')
    return json.loads(json_string)


@functions_framework.cloud_event
def predict(cloud_event):
    """
        Triggered from a message on a Cloud Pub/Sub topic.
    """
    data_bytes = base64.b64decode(cloud_event.data["message"]["data"])


    data = json.loads(data_bytes.decode("utf-8"))

    image_base64 = data.get('image_base64')
    prompt = data.get('prompt')
    google_api_model=data.get('google_api_model')
    max_output_tokens = data.get('max_output_tokens')
    temperature = data.get('temperature')
    top_k = data.get('top_k')
    top_p = data.get('top_p')

    google_api_key=get_secret()

    label = get_prediction(
      image_base64=image_base64,
      prompt=prompt,
      google_api_key=google_api_key,
      google_api_model=google_api_model,
      max_output_tokens=max_output_tokens,
      temperature=temperature,
      top_k=top_k,
      top_p=top_p,
    )

    print(label)