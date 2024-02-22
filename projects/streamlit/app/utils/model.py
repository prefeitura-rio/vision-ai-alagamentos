# -*- coding: utf-8 -*-
import base64
import io
import json
import os

import requests
from PIL import Image


def encode_image_to_base64(image):
    # if image is str convert to BytesIO
    if isinstance(image, str):
        with Image.open(image) as img:
            buffered = io.BytesIO()
            img.save(buffered, format="JPEG")

            bytes_data = buffered.getvalue()

    else:
        bytes_data = image.getvalue()

    return base64.b64encode(bytes_data).decode("utf-8")


def vision_ai_classify_image(base64_image, prompt):
    # read OPENAI_API_KEY env
    api_key = os.environ.get("OPENAI_API_KEY")
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}

    payload = {
        "model": "gpt-4-vision-preview",
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": prompt,
                    },
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"},
                    },
                ],
            }
        ],
        "max_tokens": 300,
    }

    response = requests.post(
        "https://api.openai.com/v1/chat/completions", headers=headers, json=payload
    )
    return response.json()


def get_ai_label(response):
    if response.get("error"):
        return "Error"
    else:
        r = response["choices"][0]["message"]["content"]
        json_string = r.replace("```json\n", "").replace("\n```", "")
        json_object = json.loads(json_string)
        return json_object["flooding_detected"]


def run_model(img, prompt):
    base64_image = encode_image_to_base64(img)
    response = vision_ai_classify_image(base64_image, prompt)

    return get_ai_label(response)
