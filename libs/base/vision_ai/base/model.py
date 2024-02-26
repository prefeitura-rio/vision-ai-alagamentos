# -*- coding: utf-8 -*-
import json

import cv2
import numpy as np
import pandas as pd
import requests
from PIL import Image
from vertexai.preview.generative_models import GenerativeModel, Part
from vision_ai.base.shared_models import GenerationResponseProblem, get_parser


class Model:
    def llm_vertexai(
        self,
        image_url: str,
        prompt: str,
        google_api_model: str,
        max_output_tokens: int,
        temperature: float,
        top_k: int,
        top_p: int,
        safety_settings: dict,
    ):

        image_response = requests.get(image_url)
        image_problem = self.analyze_image_problems(image_response)

        if image_problem == "ok":
            model = GenerativeModel(google_api_model)
            responses = model.generate_content(
                contents=[prompt, Part.from_data(image_response.content, "image/png")],
                generation_config={
                    "max_output_tokens": max_output_tokens,
                    "temperature": temperature,
                    "top_k": top_k,
                    "top_p": top_p,
                },
                safety_settings=safety_settings,
            )
            return responses
        elif image_problem == "green":
            return GenerationResponseProblem(
                raw_response=json.dumps(
                    {
                        "objects": [
                            {
                                "object": "image_corrupted",
                                "label_explanation": "Green corruption detected before model prediction.",
                                "label": "true",
                            }
                        ]
                    },
                    indent=4,
                )
            )
        elif image_problem == "grey":
            return GenerationResponseProblem(
                raw_response=json.dumps(
                    {
                        "objects": [
                            {
                                "object": "image_corrupted",
                                "label_explanation": "Grey corruption detected before model prediction.",
                                "label": "true",
                            }
                        ]
                    },
                    indent=4,
                )
            )

    def predict_batch(self, model_input=None, parameters=None, retry=5):
        final_predictions = pd.DataFrame()
        snapshot_urls = model_input["snapshot_url"].unique().tolist()
        lenght = len(snapshot_urls)
        # Make parallel
        for i, snapshot_url in enumerate(snapshot_urls):
            print(f"{i}/{lenght}: {snapshot_url}")
            snapshot_df = model_input[model_input["snapshot_url"] == snapshot_url]
            retry_count = retry
            while retry_count > 0:
                try:
                    responses = self.llm_vertexai(
                        image_url=snapshot_url,
                        prompt=parameters["prompt"],
                        google_api_model=parameters["google_api_model"],
                        max_output_tokens=parameters["max_output_tokens"],
                        temperature=parameters["temperature"],
                        top_k=parameters["top_k"],
                        top_p=parameters["top_p"],
                        safety_settings=parameters["safety_settings"],
                    )
                    ai_response = responses.text
                    output_parser, _, _ = get_parser()
                    ai_response_parsed = output_parser.parse(ai_response).dict()
                    prediction = pd.DataFrame.from_dict(ai_response_parsed["objects"])
                    prediction = prediction[["object", "label", "label_explanation"]].rename(
                        columns={"label": "label_ia"}
                    )
                    final_prediction = snapshot_df.merge(prediction, on="object", how="left")
                    final_predictions = pd.concat([final_predictions, final_prediction])

                    retry_count = 0
                except Exception as exception:

                    if retry_count == 0:
                        raise exception
                    else:
                        retry_count -= 1
                        print(f"Retrying {retry_count}...\nError:{exception}")

        return final_predictions

    def analyze_image_problems(self, image_response):
        GREEN_STRIPES_THRESHOLD = 0.0001
        GREY_IMAGE_THRESHOLD = 0.3
        # Read the image from the response
        image = np.frombuffer(image_response.content, np.uint8)
        image = cv2.imdecode(image, cv2.IMREAD_COLOR)

        image_pil = Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
        image_data = np.array(image_pil)

        means = np.mean(image_data, axis=(0, 1))
        std_devs = np.std(image_data, axis=(0, 1))

        # Probability of green stripes
        green_stripe_prob = (
            min(max((means[1] - 1.5 * max(means[0], means[2])) / std_devs[1], 0), 1)
            if std_devs[1] != 0
            else 0
        )

        # Probability of grey image
        grey_image_prob = (
            min(max((10 - np.max(np.abs(means - np.mean(means)))) / np.mean(std_devs), 0), 1)
            if np.mean(std_devs) != 0
            else 0
        )

        if green_stripe_prob > GREEN_STRIPES_THRESHOLD:
            return "green"
        elif grey_image_prob > GREY_IMAGE_THRESHOLD:
            return "grey"
        else:
            return "ok"
