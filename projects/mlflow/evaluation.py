# -*- coding: utf-8 -*-
import json

import matplotlib.pyplot as plt
import mlflow
import pandas as pd
import seaborn as sns
import vertexai
from sklearn.metrics import confusion_matrix
from vertexai.preview import generative_models
from vision_ai.base.metrics import calculate_metrics
from vision_ai.base.model import Model
from vision_ai.base.pandas import explode_df
from vision_ai.base.prompt import get_prompt
from vision_ai.base.sheets import get_objects_table_from_sheets

# import os
# os.environ["MLFLOW_TRACKING_USERNAME"] = secret["mlflow_tracking_username"]
# os.environ["MLFLOW_TRACKING_PASSWORD"] = secret["mlflow_tracking_password"]

PROJECT_ID = "rj-escritorio-dev"
LOCATION = "us-central1"
VERSION_ID = "latest"
DATASET_ID = "vision_ai"
TABLE_ID = "cameras_predicoes"
vertexai.init(project=PROJECT_ID, location=LOCATION)

SAFETY_CONFIG = {
    generative_models.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: generative_models.HarmBlockThreshold.BLOCK_NONE,
    generative_models.HarmCategory.HARM_CATEGORY_HARASSMENT: generative_models.HarmBlockThreshold.BLOCK_NONE,
    generative_models.HarmCategory.HARM_CATEGORY_HATE_SPEECH: generative_models.HarmBlockThreshold.BLOCK_NONE,
    generative_models.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: generative_models.HarmBlockThreshold.BLOCK_NONE,
}

with open("./projects/mlflow/snapshots_mock.json") as f:
    snapshots = json.load(f)

with open("./projects/mlflow/prompt.md") as f:
    prompt_text_local = f.read()


df = pd.DataFrame(snapshots)
df = explode_df(df, "human_identifications")
df = df.drop(columns=["ia_identifications"])
df = df.sort_values(by=["snapshot_id", "object", "count"], ascending=False)
df = df.drop_duplicates(subset=["snapshot_id", "object"], keep="first")


objects_table_md, objects_labels_md = get_objects_table_from_sheets()
prompt, prompt_template = get_prompt(
    prompt_parameters=None, prompt_template=prompt_text_local, objects_table_md=objects_table_md
)


google_api_model = "gemini-pro-vision"
max_output_tokens = 2048
temperature = 0.2
top_k = 32
top_p = 1


model = Model()
parameters = {
    "prompt": prompt,
    "google_api_model": google_api_model,
    "temperature": temperature,
    "top_k": top_k,
    "top_p": top_p,
    "max_output_tokens": max_output_tokens,
    "safety_settings": SAFETY_CONFIG,
}


# START PREDICTIONS
final_predictions = model.predict_batch(model_input=df, parameters=parameters)

parameters.pop("prompt")
parameters["safety_settings"] = json.dumps(SAFETY_CONFIG, indent=4)

mlflow.set_tracking_uri(uri="https://mlflow.dados.rio")

# Create a new MLflow Experiment
mlflow.set_experiment("test")

# Start an MLflow run
with mlflow.start_run():
    # Log the hyperparameter
    mlflow.log_params(parameters)
    mlflow.log_text(prompt, "prompt.md")
    mlflow.log_input(mlflow.data.from_pandas(df), context="input")
    mlflow.log_input(mlflow.data.from_pandas(final_predictions), context="output")

    # Calculate metrics for each object
    results = {}
    for obj in final_predictions["object"].unique():
        df_obj = final_predictions[final_predictions["object"] == obj]
        y_true = df_obj["label"]
        y_pred = df_obj["label_ia"]

        # Choose an appropriate average method (e.g., 'micro', 'macro', or 'weighted')
        average_method = "macro"
        accuracy, precision, recall, f1 = calculate_metrics(y_true, y_pred, average_method)
        unique_labels = sorted(set(y_true) | set(y_pred))
        cm = confusion_matrix(y_true, y_pred, labels=unique_labels)

        plt.figure(figsize=(8, 6))
        sns.heatmap(
            cm,
            annot=True,
            fmt="d",
            cmap="Blues",
            xticklabels=unique_labels,
            yticklabels=unique_labels,
        )
        plt.ylabel("Actual")
        plt.xlabel("Predicted")
        plt.title(f"Confusion Matrix for {obj}")
        # Save image temporarily
        temp_image_path = f"/tmp/cm_{obj}.png"
        plt.savefig(temp_image_path)

        metrics = {
            f"{obj}_accuracy": accuracy,
            f"{obj}_precision": precision,
            f"{obj}_recall": recall,
            f"{obj}_f1_score": f1,
        }
        mlflow.log_metrics(metrics)
        mlflow.log_artifact(f"/tmp/cm_{obj}.png")


# def _get_prediction(
#     image_url: str,
#     prompt_text: str,
#     google_api_model: str,
#     max_output_tokens: int,
#     temperature: float,
#     top_k: int,
#     top_p: int,
# ) -> Dict:

#     try:

#         from langchain.chains import LLMChain
#         from langchain.prompts import ChatPromptTemplate
#         from langchain_core.messages import HumanMessage
#         from langchain_google_vertexai import VertexAI

#         model = VertexAI(
#             model_name=google_api_model,
#             temperature=temperature,
#             top_k=top_k,
#             top_p=top_p,
#             max_output_tokens=max_output_tokens,
#             safety_settings=SAFETY_CONFIG,
#             project=PROJECT_ID,
#             location=LOCATION,
#         )

#         content = [
#             {"type": "image_url", "image_url": {"url": image_url}},
#             {
#                 "type": "text",
#                 "text": prompt_text,
#             },
#         ]
#         message = HumanMessage(content=content)

#         chain = LLMChain(llm=model, prompt=ChatPromptTemplate.from_messages([message]))
#         ai_response = chain.invoke({})["text"]

#     except Exception as exception:
#         raise exception

#     output_parser, _, _ = get_parser()

#     try:
#         response_parsed = output_parser.parse(ai_response)
#     except Exception as exception:
#         raise exception

#     return response_parsed.dict()
