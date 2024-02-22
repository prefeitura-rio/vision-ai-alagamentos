# -*- coding: utf-8 -*-
import pandas as pd
import requests
from langchain.output_parsers import PydanticOutputParser
from vertexai.preview.generative_models import GenerativeModel, Part
from vision_ai.base.shared_models import Output


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

    def predict_batch(
        self,
        model_input=None,
        params=None,
    ):
        final_predictions = pd.DataFrame()
        for snapshot_id in model_input["snapshot_id"].unique().tolist():
            snapshot_df = model_input[model_input["snapshot_id"] == snapshot_id]
            responses = self.llm_vertexai(
                image_url=snapshot_id,
                prompt=params["prompt"],
                google_api_model=params["google_api_model"],
                max_output_tokens=params["max_output_tokens"],
                temperature=params["temperature"],
                top_k=params["top_k"],
                top_p=params["top_p"],
            )
            ai_response = responses.text
            output_parser = PydanticOutputParser(pydantic_object=Output)
            predictions = output_parser.parse(ai_response)

            prediction = pd.DataFrame.from_dict(predictions["objects"])
            prediction = prediction[["object", "label", "label_explanation"]].rename(
                columns={"label": "label_ia"}
            )
            final_prediction = snapshot_df.merge(prediction, on="object", how="left")
            final_predictions = pd.concat([final_predictions, final_prediction])
        return final_predictions
