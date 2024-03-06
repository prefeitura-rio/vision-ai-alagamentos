# -*- coding: utf-8 -*-
import json
import os
import shutil
import time
from pathlib import Path

import matplotlib.pyplot as plt
import mlflow
import pandas as pd
import seaborn as sns
import vertexai
from sklearn.metrics import confusion_matrix, recall_score
from vertexai.preview import generative_models
from vision_ai.base.api import VisionaiAPI
from vision_ai.base.metrics import calculate_metrics
from vision_ai.base.model import Model
from vision_ai.base.pandas import explode_df
from vision_ai.base.prompt import get_prompt_api, get_prompt_local
from vision_ai.base.sheets import get_objects_table_from_sheets

PROJECT_ID = "rj-vision-ai"
LOCATION = "us-central1"
vertexai.init(project=PROJECT_ID, location=LOCATION)
SAFETY_CONFIG = {
    generative_models.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: generative_models.HarmBlockThreshold.BLOCK_NONE,
    generative_models.HarmCategory.HARM_CATEGORY_HARASSMENT: generative_models.HarmBlockThreshold.BLOCK_NONE,
    generative_models.HarmCategory.HARM_CATEGORY_HATE_SPEECH: generative_models.HarmBlockThreshold.BLOCK_NONE,
    generative_models.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: generative_models.HarmBlockThreshold.BLOCK_NONE,
}

ABSOLUTE_PATH = Path(__file__).parent.absolute()
ARTIFACT_PATH = Path("/tmp/ml_flow_artifacts")
ARTIFACT_PATH.mkdir(exist_ok=True, parents=True)


def load_data(use_mock_snapshots=False, save_mock_snapshots=False, use_local_prompt=False):
    mock_snapshot_data_path = ABSOLUTE_PATH / "mock_snapshots_api_data.json"

    vision_api = VisionaiAPI(
        username=os.environ.get("VISION_API_USERNAME"),
        password=os.environ.get("VISION_API_PASSWORD"),
    )
    # GET PROMPT FROM API
    prompt_data = vision_api._get_all_pages(path="/prompts")
    objects_data = vision_api._get_all_pages(path="/objects")
    prompt_parameters, _ = get_prompt_api(
        prompt_name="base", prompt_data=prompt_data, objects_data=objects_data
    )
    if use_local_prompt:
        # LOCAL PROMPT + OBJECTS TABLE FROM SHEETS
        with open("./projects/mlflow/prompt.md") as f:
            prompt_text_local = f.read()
        objects_table_md, _ = get_objects_table_from_sheets()
        prompt, _ = get_prompt_local(
            prompt_parameters=None,
            prompt_template=prompt_text_local,
            objects_table_md=objects_table_md,
        )
        prompt_parameters["prompt_text"] = prompt

    if use_mock_snapshots:
        with open(mock_snapshot_data_path, "r") as f:
            snapshots = json.load(f)
    else:
        snapshots = vision_api._get(path="/identifications/aggregate")

    if save_mock_snapshots:
        with open(mock_snapshot_data_path, "w") as f:
            json.dump(snapshots, f)

    dataframe = pd.DataFrame(snapshots)
    dataframe = explode_df(dataframe, "human_identification")
    dataframe = dataframe.drop(columns=["ia_identification"])
    dataframe = dataframe.sort_values(by=["snapshot_id", "object", "count"], ascending=False)
    dataframe = dataframe.drop_duplicates(subset=["snapshot_id", "object"], keep="first")

    # Calculate metrics for each object
    dataframe_balance = (
        dataframe[["object", "label", "count"]].groupby(["object", "label"], as_index=False).count()
    )
    dataframe_balance["percentage"] = round(
        dataframe_balance["count"] / dataframe_balance["count"].sum(), 2
    )

    return dataframe, dataframe_balance, prompt_parameters


def make_predictions(dataframe, parameters, use_mock_predictions=False, max_workers=10):
    mock_final_predicition_path = ABSOLUTE_PATH / "mock_final_predictions.csv"

    model = Model()
    parameters = {
        "prompt_text": parameters["prompt_text"],
        "google_api_model": parameters["google_api_model"],
        "temperature": parameters["temperature"],
        "top_k": parameters["top_k"],
        "top_p": parameters["top_p"],
        "max_output_tokens": parameters["max_output_tokens"],
        "safety_settings": SAFETY_CONFIG,
    }
    if use_mock_predictions:
        final_predictions = pd.read_csv(mock_final_predicition_path)
    else:
        final_predictions = model.predict_batch_mlflow(
            model_input=dataframe, parameters=parameters, max_workers=max_workers
        )
        final_predictions.to_csv(mock_final_predicition_path, index=False)

    final_predictions["label"] = final_predictions["label"].fillna("null")
    final_predictions["label_ia"] = final_predictions["label_ia"].fillna("null")
    final_predictions["label_ia"] = final_predictions["label_ia"].apply(lambda x: str(x).lower())
    mask = (final_predictions["object"] == "image_corrupted") & (
        final_predictions["label_ia"] == "prediction_error"
    )

    final_predictions_errors = final_predictions[mask]
    final_predictions = final_predictions[~mask]

    parameters["number_errors"] = len(final_predictions_errors["snapshot_id"].unique())

    return final_predictions, final_predictions_errors, parameters


def mlflow_log(
    experiment_name,
    input,
    output,
    input_balance,
    output_erros,
    parameters,
):
    # Set up MLflow tracking

    artifact_input_path = ARTIFACT_PATH / "input.csv"
    artifact_output_path = ARTIFACT_PATH / "output.csv"
    artifact_output_errors_path = ARTIFACT_PATH / "output_erros.csv"
    artifact_input_balance_path = ARTIFACT_PATH / "input_balance.csv"

    input.to_csv(artifact_input_path, index=False)
    output.to_csv(artifact_output_path, index=False)
    output_erros.to_csv(artifact_output_errors_path, index=False)
    input_balance.to_csv(artifact_input_balance_path, index=False)

    mlflow.set_tracking_uri(uri="https://mlflow.dados.rio")
    mlflow.set_experiment(experiment_name)

    with mlflow.start_run():
        # Log the hyperparameter
        mlflow.log_text(parameters["prompt_text"], "prompt.md")
        parameters.pop("prompt_text")
        mlflow.log_params(parameters)

        mlflow.log_artifact(artifact_input_path)
        mlflow.log_artifact(artifact_output_path)
        if len(output_erros) > 0:
            mlflow.log_artifact(artifact_output_errors_path)
        mlflow.log_artifact(artifact_input_balance_path)

        for obj in output["object"].unique():
            df_obj = output[output["object"] == obj]
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
            temp_image_path = ARTIFACT_PATH / f"cm_{obj}.png"
            plt.savefig(temp_image_path)

            if obj == "image_corrupted":
                mlflow.log_metric(f"{obj}_recall", recall)
                mlflow.log_metric(f"{obj}_precision", precision)
            elif obj == "rain":
                mlflow.log_metric(f"{obj}_f1_score", f1)
            elif obj in ["water_level", "road_blockade"]:
                mlflow.log_metric(f"{obj}_recall", recall)
                recall_per_label = recall_score(
                    y_true, y_pred, average=None, labels=unique_labels, zero_division=0
                )
                for i, label in enumerate(unique_labels):
                    if label not in ["null", "free", "low"]:
                        mlflow.log_metric(f"{obj}_{label}_recall", recall_per_label[i])
            # mlflow.log_metrics(metrics)
            mlflow.log_artifact(temp_image_path)

    shutil.rmtree(ARTIFACT_PATH)


if __name__ == "__main__":
    start_time = time.time()
    dataframe, dataframe_balance, parameters = load_data(save_mock_snapshots=True)
    parameters = {
        "prompt_text": parameters["prompt_text"],
        "google_api_model": "gemini-pro-vision",
        "max_output_tokens": 2048,
        "temperature": 0.2,
        "top_k": 32,
        "top_p": 1,
        "safety_settings": SAFETY_CONFIG,
    }

    print("\nStart Predictions\n")
    final_predictions, final_predictions_errors, parameters = make_predictions(
        dataframe=dataframe, parameters=parameters, use_mock_predictions=False, max_workers=50
    )
    tag = "temperature-stability"
    today = pd.Timestamp.now().strftime("%Y-%m-%d")
    experiment_name = f"{today}-{tag}"

    print("\nStart MLflow logging\n")
    mlflow_log(
        experiment_name=experiment_name,
        input=dataframe,
        output=final_predictions,
        input_balance=dataframe_balance,
        output_erros=final_predictions_errors,
        parameters=parameters,
    )
    print(f"\nRun time: {time.time() - start_time}")
