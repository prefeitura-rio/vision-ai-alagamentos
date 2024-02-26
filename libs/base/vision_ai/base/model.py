# -*- coding: utf-8 -*-
import pandas as pd
import requests
from vertexai.preview.generative_models import GenerativeModel, Part
from vision_ai.base.shared_models import get_parser


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
