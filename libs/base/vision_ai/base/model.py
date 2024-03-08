# -*- coding: utf-8 -*-
import json
import time
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed

import cv2
import numpy as np
import pandas as pd
import requests
from PIL import Image
from vertexai.preview.generative_models import GenerativeModel, Part
from vision_ai.base.shared_models import GenerationResponseProblem, get_parser


class Model:
    def test(self):
        model = GenerativeModel("gemini-pro")
        responses = model.generate_content(contents=["Tell me a joke about dogs"])
        print(responses)

    def llm_vertexai(
        self,
        image_url: str,
        prompt_text: str,
        google_api_model: str,
        max_output_tokens: int,
        temperature: float,
        top_k: int,
        top_p: int,
        safety_settings: dict,
    ):

        image_response = requests.get(image_url)
        image_problem = self.analyze_image_problems(image_response)
        image_format = image_url.split(".")[-1]
        if image_problem == "ok":
            model = GenerativeModel(google_api_model)
            responses = model.generate_content(
                contents=[
                    prompt_text,
                    Part.from_data(image_response.content, f"image/{image_format}"),
                ],
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

    def predict_batch_mlflow(
        self, model_input=None, parameters=None, retry=5, max_workers=10
    ):
        def process_url(snapshot_url, index, total, retry, output_parser):
            start_time = time.time()
            snapshot_df = model_input[model_input["snapshot_url"] == snapshot_url]
            for i in range(retry):
                try:
                    response = self.llm_vertexai(
                        image_url=snapshot_url,
                        prompt_text=parameters["prompt_text"],
                        google_api_model=parameters["google_api_model"],
                        max_output_tokens=parameters["max_output_tokens"],
                        temperature=parameters["temperature"],
                        top_k=parameters["top_k"],
                        top_p=parameters["top_p"],
                        safety_settings=parameters["safety_settings"],
                    ).text
                    ai_response_parsed = output_parser.parse(response).dict()

                    prediction = pd.DataFrame(ai_response_parsed["objects"])[
                        ["object", "label", "label_explanation"]
                    ].rename(columns={"label": "label_ia"})
                    print(
                        f"Predicted {index}/{total} in {time.time() - start_time:.2f} seconds: {snapshot_url}"
                    )
                    return snapshot_df.merge(prediction, on="object", how="left")
                except Exception as exception:
                    error_name = (str(type(exception).__name__),)
                    error = str(traceback.format_exc(chain=False))

                    error_str = f"{error_name}: {error}"
                    print(f"Retrying {index}/{total}, retries left {retry -i -1}")

            prediction_error = snapshot_df.merge(
                pd.DataFrame(
                    [
                        {
                            "object": "image_corrupted",
                            "label_ia": "prediction_error",
                            "label_explanation": f"Error: {error_str}",
                        }
                    ]
                ),
                on="object",
                how="left",
            )
            mask = (prediction_error["object"] == "image_corrupted") & (
                prediction_error["label_ia"] == "prediction_error"
            )
            prediction_error = prediction_error[mask]
            return prediction_error

        output_parser, _, _ = get_parser()
        snapshot_urls = model_input["snapshot_url"].unique().tolist()
        total_images = len(snapshot_urls)

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [
                executor.submit(
                    process_url, url, i + 1, total_images, retry, output_parser
                )
                for i, url in enumerate(snapshot_urls)
            ]
            results = [future.result() for future in as_completed(futures)]

        return pd.concat(results, ignore_index=True)

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
            min(
                max(
                    (10 - np.max(np.abs(means - np.mean(means)))) / np.mean(std_devs), 0
                ),
                1,
            )
            if np.mean(std_devs) != 0
            else 0
        )

        if green_stripe_prob > GREEN_STRIPES_THRESHOLD:
            return "green"
        elif grey_image_prob > GREY_IMAGE_THRESHOLD:
            return "grey"
        else:
            return "ok"
