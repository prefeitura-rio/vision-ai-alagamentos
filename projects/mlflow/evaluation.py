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
from vision_ai.base.metrics import (
    calculate_metrics,
    crossentropy,
    water_level_custom_metric,
)
from vision_ai.base.model import Model
from vision_ai.base.pandas import handle_snapshots_df
from vision_ai.base.prompt import get_prompt_api, get_prompt_local
from vision_ai.base.sheets import get_objects_table_from_sheets, create_google_sheet_from_dataframe

# Assert all environment variables are set
for var in [
    "MLFLOW_TRACKING_USERNAME",
    "MLFLOW_TRACKING_PASSWORD",
    "VISION_API_USERNAME",
    "VISION_API_PASSWORD",
]:
    assert os.environ.get(var), f"Environment variable {var} is not set"

PROJECT_ID = "rj-vision-ai"
LOCATION = "us-central1"
vertexai.init(project=PROJECT_ID, location=LOCATION)
# SHEETS_URL = getenv("SHEETS_URL")
SAFETY_CONFIG = {
    generative_models.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: generative_models.HarmBlockThreshold.BLOCK_NONE,
    generative_models.HarmCategory.HARM_CATEGORY_HARASSMENT: generative_models.HarmBlockThreshold.BLOCK_NONE,
    generative_models.HarmCategory.HARM_CATEGORY_HATE_SPEECH: generative_models.HarmBlockThreshold.BLOCK_NONE,
    generative_models.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: generative_models.HarmBlockThreshold.BLOCK_NONE,
}

ABSOLUTE_PATH = Path(__file__).parent.absolute()
ARTIFACT_PATH = Path("/tmp/ml_flow_artifacts")


def load_data(
    use_mock_snapshots=False,
    save_mock_snapshots=False,
    use_local_prompt=None,
    object_sheet_url=None,
):
    mock_snapshot_data_path = ABSOLUTE_PATH / "mock_snapshots_api_data.json"

    vision_api = VisionaiAPI(
        username=os.environ.get("VISION_API_USERNAME"),
        password=os.environ.get("VISION_API_PASSWORD"),
    )
    # GET PROMPT FROM API
    prompt_data = vision_api._get_all_pages(path="/prompts")
    objects_data = vision_api._get_all_pages(path="/objects")
    prompt_parameters = dict()

    if use_local_prompt:
        # LOCAL PROMPT + OBJECTS TABLE FROM SHEETS
        with open(use_local_prompt, "r") as f:
            prompt_parameters["prompt_text"] = f.read()

    elif object_sheet_url:
        objects_table_md, _ = get_objects_table_from_sheets(url=object_sheet_url)
        prompt_template = [p for p in prompt_data if p["name"] == "base"][0]["prompt_text"]
        prompt, _ = get_prompt_local(
            prompt_parameters=None,
            prompt_template=prompt_template,
            objects_table_md=objects_table_md,
        )
        prompt_parameters["prompt_text"] = prompt
    else:
        prompt_parameters = get_prompt_api(
            prompt_name="base", prompt_data=prompt_data, objects_data=objects_data
        )

    if use_mock_snapshots:
        with open(mock_snapshot_data_path, "r") as f:
            snapshots = json.load(f)
    else:
        snapshots = vision_api._get(path="/identifications/aggregate")

    if save_mock_snapshots:
        with open(mock_snapshot_data_path, "w") as f:
            json.dump(snapshots, f)

    dataframe = pd.DataFrame(snapshots)
    dataframe = handle_snapshots_df(dataframe, "human_identification")

    # Calculate metrics for each object
    dataframe_balance = (
        dataframe[["object", "hard_label", "count"]]
        .groupby(["object", "hard_label"], as_index=False)
        .count()
    )
    dataframe_balance["percentage"] = round(
        dataframe_balance["count"] / dataframe_balance["count"].sum(), 2
    )
    dataframe_balance["object_percentage"] = round(
        dataframe_balance.groupby("object")["percentage"].transform("sum"), 2
    )
    # Calculating the percentage inside each object
    total_counts = dataframe_balance.groupby("object")["count"].sum()
    dataframe_balance["object_percentage"] = dataframe_balance.apply(
        lambda row: row["count"] / total_counts[row["object"]], axis=1
    )
    dataframe_balance["object_percentage"] = dataframe_balance["object_percentage"].round(2)

    return dataframe, dataframe_balance, prompt_parameters


def make_predictions(dataframe, parameters, max_workers=10, retry=5):

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

    final_predictions = model.predict_batch_mlflow(
        model_input=dataframe, parameters=parameters, max_workers=max_workers, retry=retry
    )

    mask = (final_predictions["object"] == "image_corrupted") & (
        final_predictions["label_ia"] == "prediction_error"
    )

    final_predictions_errors = final_predictions[mask]
    final_predictions = final_predictions[~mask]

    return final_predictions, final_predictions_errors, parameters


def run_experiments(
    dataframe,
    parameters,
    n_runs=5,
    use_mock_predictions=False,
    save_mock_predictions=True,
    max_workers=10,
    retry=5,
):
    mock_final_predicition_path = ABSOLUTE_PATH / "mock_final_predictions.csv"
    runs_df = pd.DataFrame()
    run_errors = pd.DataFrame()

    if use_mock_predictions and mock_final_predicition_path.exists():
        runs_df = pd.read_csv(mock_final_predicition_path, dtype=str)
    else:
        for run in range(n_runs):
            print(f"\nStart Predictions Run: {run+1}/{n_runs}\n")
            final_predictions, final_predictions_errors, parameters = make_predictions(
                dataframe=dataframe,
                parameters=parameters,
                max_workers=max_workers,
                retry=retry,
            )
            final_predictions.insert(0, "run", run)
            runs_df = pd.concat([runs_df, final_predictions])

            final_predictions_errors.insert(0, "run", run)
            run_errors = pd.concat([run_errors, final_predictions_errors])

    runs_df = clean_labels(dataframe=runs_df)

    parameters["runs"] = n_runs

    if save_mock_predictions:
        runs_df.to_csv(mock_final_predicition_path, index=False)

    return runs_df, run_errors, parameters


def mlflow_log(
    experiment_name,
    run_name,
    input,
    output,
    input_balance,
    output_erros,
    parameters,
):
    # Set up MLflow tracking
    ARTIFACT_PATH.mkdir(exist_ok=True, parents=True)
    mlflow.set_tracking_uri(uri="https://mlflow.dados.rio")
    mlflow.set_experiment(experiment_name)
    # mlflow.set_tag("mlflow.runName", run_name)
    with mlflow.start_run() as mlrun:
        # Log the hyperparameter
        mlflow.log_text(parameters["prompt_text"], "prompt.md")
        parameters.pop("prompt_text")
        if len(output_erros) > 0:
            parameters["errors"] = len(output_erros["snapshot_id"].unique())

        parameters["images"] = len(output["snapshot_id"].unique())
        parameters["safety_settings"] = json.dumps(SAFETY_CONFIG)
        mlflow.log_params(parameters)

        artifact_input_path = ARTIFACT_PATH / "input.csv"
        input.to_csv(artifact_input_path, index=False)

        artifact_input_balance_path = ARTIFACT_PATH / "input_balance.csv"
        input_balance.to_csv(artifact_input_balance_path, index=False)

        output["correct"] = output["hard_label"] == output["label_ia"]
        output = output[
            [
                "run",
                "object",
                "correct",
                "snapshot_url",
                "label_ia",
                "hard_label",
                "label_explanation",
                "label",
                "distribution",
            ]
        ]
        artifact_output_path = ARTIFACT_PATH / "output.csv"
        output.to_csv(artifact_output_path, index=False)
        # sheets_url = create_google_sheet_from_dataframe(
        #     output,
        #     f"{experiment_name}_{mlrun.info.run_id}",
        # )

        # save sheets_url in README.md and add as mlflow artifact
        with open(ARTIFACT_PATH / "README.md", "w") as f:
            f.write(f"## {experiment_name} - {run_name}\n")
            f.write(f"### [Sheets URL]({sheets_url})\n")
        mlflow.log_artifact(ARTIFACT_PATH / "README.md")

        artifact_output_errors_path = ARTIFACT_PATH / "output_erros.csv"
        output_erros.to_csv(artifact_output_errors_path, index=False)

        mlflow.log_artifact(artifact_input_path)
        mlflow.log_artifact(artifact_output_path)
        if len(output_erros) > 0:
            mlflow.log_artifact(artifact_output_errors_path)
        mlflow.log_artifact(artifact_input_balance_path)

        metrics_df = pd.DataFrame()
        for run in output["run"].unique().tolist():
            output_run = output[output["run"] == run]
            for obj in output_run["object"].unique():
                df_obj = output_run[output_run["object"] == obj]
                y_true = df_obj["hard_label"]
                y_pred = df_obj["label_ia"]
                true_labels = df_obj["label"]
                true_probs = df_obj["distribution"]
                # Choose an appropriate average method (e.g., 'micro', 'macro', or 'weighted')
                average_method = "macro"
                accuracy, precision, recall, f1 = calculate_metrics(y_true, y_pred, average_method)
                crossentropy_loss_mean, crossentropy_loss_std = crossentropy(
                    true_labels, true_probs, y_pred
                )
                Xrecall_high, Xrecall_medium = water_level_custom_metric(
                    y_true=y_true, y_pred=y_pred
                )

                unique_labels = sorted(set(y_true) | set(y_pred))

                recall_per_label = recall_score(
                    y_true, y_pred, average=None, labels=unique_labels, zero_division=0
                )
                for i, label in enumerate(unique_labels):
                    metrics_df = pd.concat(
                        [
                            metrics_df,
                            pd.DataFrame(
                                [
                                    {
                                        "run": run,
                                        "object": obj,
                                        "label": label,
                                        "accuracy": accuracy,
                                        "precision": precision,
                                        "recall": recall,
                                        "f1": f1,
                                        "crossentropy_loss_mean": crossentropy_loss_mean,
                                        "crossentropy_loss_std": crossentropy_loss_std,
                                        "label_recall": recall_per_label[i],
                                        "Xrecall_high": Xrecall_high if obj == "water_level" else 0,
                                        "Xrecall_medium": (
                                            Xrecall_medium if obj == "water_level" else 0
                                        ),
                                    }
                                ]
                            ),
                        ]
                    )

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
                temp_image_path = ARTIFACT_PATH / f"cm_{obj}_{run}.png"
                plt.savefig(temp_image_path)
                mlflow.log_artifact(temp_image_path)

        artifact_output_metrics_path = ARTIFACT_PATH / "metrics.csv"
        metrics_df.to_csv(artifact_output_metrics_path, index=False)
        mlflow.log_artifact(artifact_output_metrics_path)

        cols = [
            "object",
            "accuracy",
            "precision",
            "recall",
            "f1",
            "crossentropy_loss_mean",
            "crossentropy_loss_std",
            "Xrecall_high",
            "Xrecall_medium",
        ]
        object_metrics = metrics_df[cols].groupby("object", as_index=False).mean()
        artifact_metrics_objects_path = ARTIFACT_PATH / "metrics_objects.csv"
        object_metrics.to_csv(artifact_metrics_objects_path, index=False)
        mlflow.log_artifact(artifact_metrics_objects_path)

        cols = ["object", "label", "label_recall"]
        label_metrics = metrics_df[cols].groupby(["object", "label"], as_index=False).mean()
        artifact_metrics_labels_path = ARTIFACT_PATH / "metrics_labels.csv"
        label_metrics.to_csv(artifact_metrics_labels_path, index=False)
        mlflow.log_artifact(artifact_metrics_labels_path)

        mask = (label_metrics["object"].isin(["road_blockade", "water_level"])) & (
            label_metrics["label"].isin(["partially", "totally", "medium", "high"])
        )
        label_metrics_filtered = label_metrics[mask]
        artifact_metrics_labels_filterd_path = ARTIFACT_PATH / "metrics_labels_filtered.csv"
        label_metrics_filtered.to_csv(artifact_metrics_labels_filterd_path, index=False)
        mlflow.log_artifact(artifact_metrics_labels_filterd_path)

        for _, row in object_metrics.iterrows():
            obj = row["object"]

            if obj == "image_corrupted":
                mlflow.log_metric(f"{obj}_recall", row["recall"])
                mlflow.log_metric(f"{obj}_precision", row["precision"])
                mlflow.log_metric(f"{obj}_crossentropy_loss", row["crossentropy_loss_mean"])
                mlflow.log_metric(f"{obj}_crossentropy_loss_std", row["crossentropy_loss_std"])
            elif obj == "rain":
                mlflow.log_metric(f"{obj}_f1_score", row["f1"])
                mlflow.log_metric(f"{obj}_crossentropy_loss", row["crossentropy_loss_mean"])
                mlflow.log_metric(f"{obj}_crossentropy_loss_std", row["crossentropy_loss_std"])
            elif obj == "water_level":
                mlflow.log_metric(f"{obj}_precision", row["precision"])
                mlflow.log_metric(f"{obj}_accuracy", row["accuracy"])
                mlflow.log_metric(f"{obj}_recall", row["recall"])
                mlflow.log_metric(f"{obj}_crossentropy_loss", row["crossentropy_loss_mean"])
                mlflow.log_metric(f"{obj}_crossentropy_loss_std", row["crossentropy_loss_std"])
                mlflow.log_metric(f"{obj}_Xrecall_high", row["Xrecall_high"])
                mlflow.log_metric(f"{obj}_Xrecall_medium", row["Xrecall_medium"])

                for _, label_row in label_metrics_filtered.iterrows():
                    label = label_row["label"]
                    if label in ["medium", "high"]:
                        mlflow.log_metric(f"{obj}_{label}_recall", label_row["label_recall"])
            elif obj == "road_blockade":
                mlflow.log_metric(f"{obj}_recall", row["recall"])
                mlflow.log_metric(f"{obj}_crossentropy_loss", row["crossentropy_loss_mean"])
                mlflow.log_metric(f"{obj}_crossentropy_loss_std", row["crossentropy_loss_std"])
                for _, label_row in label_metrics_filtered.iterrows():
                    label = label_row["label"]
                    if label in ["partially", "totally"]:
                        mlflow.log_metric(f"{obj}_{label}_recall", label_row["label_recall"])

    shutil.rmtree(ARTIFACT_PATH)


def clean_labels(dataframe):
    dataframe["label_ia"] = dataframe["label_ia"].astype(str)
    replacer = ["\n", "{", "}", "[", "]"]
    for replace in replacer:
        dataframe["label_ia"] = dataframe["label_ia"].str.replace(replace, "")
    dataframe["label_ia"] = dataframe["label_ia"].str.strip()
    dataframe["label_ia"] = dataframe["label_ia"].fillna("null")
    dataframe["label_ia"] = dataframe["label_ia"].fillna("null")
    dataframe["label_ia"] = dataframe["label_ia"].apply(lambda x: str(x).lower())
    dataframe["label_ia"] = dataframe["label_ia"].str.replace("nan", "null")

    dataframe["hard_label"] = dataframe["hard_label"].fillna("null")
    dataframe["hard_label"] = dataframe["hard_label"].apply(lambda x: str(x).lower())
    dataframe["hard_label"] = dataframe["hard_label"].str.replace("nan", "null")

    return dataframe


if __name__ == "__main__":
    tag = "water-minimal-baselines"
    today = pd.Timestamp.now().strftime("%Y-%m-%d")
    experiment_name = f"{today}-{tag}"
    sheets_urls = {
        # "base": "https://docs.google.com/spreadsheets/d/122uOaPr8YdW5PTzrxSPF-FD0tgco596HqgB7WK7cHFw/edit#gid=1672006844",
        # "random": "https://docs.google.com/spreadsheets/d/122uOaPr8YdW5PTzrxSPF-FD0tgco596HqgB7WK7cHFw/edit#gid=1377715485",
        # "vague": "https://docs.google.com/spreadsheets/d/122uOaPr8YdW5PTzrxSPF-FD0tgco596HqgB7WK7cHFw/edit#gid=2004312781",
        # "empty": "https://docs.google.com/spreadsheets/d/122uOaPr8YdW5PTzrxSPF-FD0tgco596HqgB7WK7cHFw/edit#gid=568577633",
        # "vehicle": "https://docs.google.com/spreadsheets/d/122uOaPr8YdW5PTzrxSPF-FD0tgco596HqgB7WK7cHFw/edit#gid=55110964",
        # "vehicle_diff": "https://docs.google.com/spreadsheets/d/122uOaPr8YdW5PTzrxSPF-FD0tgco596HqgB7WK7cHFw/edit#gid=1337396877",
        # "pedestrian": "https://docs.google.com/spreadsheets/d/122uOaPr8YdW5PTzrxSPF-FD0tgco596HqgB7WK7cHFw/edit#gid=1432557618",
        "sidewalk": "https://docs.google.com/spreadsheets/d/122uOaPr8YdW5PTzrxSPF-FD0tgco596HqgB7WK7cHFw/edit#gid=912988762",
        # "water_depth": "https://docs.google.com/spreadsheets/d/122uOaPr8YdW5PTzrxSPF-FD0tgco596HqgB7WK7cHFw/edit#gid=981358768",
        # "vehicle_wheel": "https://docs.google.com/spreadsheets/d/122uOaPr8YdW5PTzrxSPF-FD0tgco596HqgB7WK7cHFw/edit#gid=1657724821",
        # "sidewalk_aggressive": "https://docs.google.com/spreadsheets/d/122uOaPr8YdW5PTzrxSPF-FD0tgco596HqgB7WK7cHFw/edit#gid=929890265",
    }
    start_time = time.time()
    for key, value in sheets_urls.items():
        print(f"Start prompt {key}")
        dataframe, dataframe_balance, original_parameters = load_data(
            use_mock_snapshots=False,
            save_mock_snapshots=True,
            use_local_prompt=False,
            object_sheet_url=value,
        )

        parameters = {
            "prompt_text": original_parameters["prompt_text"],
            "google_api_model": "gemini-pro-vision",
            "max_output_tokens": 2048,
            "temperature": 0.15,  # 0-1
            "top_k": 10,  # 1-40
            "top_p": 0.9,  # 0-1
            "safety_settings": SAFETY_CONFIG,
        }

        runs_df, run_errors, parameters = run_experiments(
            dataframe=dataframe,
            parameters=parameters,
            n_runs=1,
            use_mock_predictions=False,
            save_mock_predictions=True,
            max_workers=75,
        )

        print("\nStart MLflow logging\n")

        parameters["prompt_name"] = key

        mlflow_log(
            experiment_name=experiment_name,
            run_name=key,
            input=dataframe,
            output=runs_df,
            input_balance=dataframe_balance,
            output_erros=run_errors,
            parameters=parameters,
        )

        print(f"\nRun time: {time.time() - start_time}")
