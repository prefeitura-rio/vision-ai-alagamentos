# -*- coding: utf-8 -*-
import io
import json
import textwrap
from typing import Dict, List, Union

import matplotlib.pyplot as plt
import mlflow
import pandas as pd
import requests
import seaborn as sns
import vertexai
from langchain.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
)
from vertexai.preview import generative_models
from vertexai.preview.generative_models import GenerativeModel, Part

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


class Object(BaseModel):
    object: str = Field(description="The object from the objects")
    label_explanation: str = Field(
        description="Highly detailed visual description of the image given the object context"
    )
    label: Union[bool, str, None] = Field(
        description="Label indicating the condition or characteristic of the object"
    )


class ObjectFactory:
    @classmethod
    def generate_sample(cls) -> Object:
        return Object(
            object="<Object from objects>",
            label_explanation="<Visual description of the image given the object context>",
            label="<Selected label from objects>",
        )


class Output(BaseModel):
    objects: List[Object]


class OutputFactory:
    @classmethod
    def generate_sample(cls) -> Output:
        return Output(objects=[ObjectFactory.generate_sample()])


class OutputFactory:
    @classmethod
    def generate_sample(cls) -> Output:
        return Output(objects=[ObjectFactory.generate_sample()])


def get_parser():

    # Create the output parser using the Pydantic model
    output_parser = PydanticOutputParser(pydantic_object=Output)

    # Valid JSON string
    output_example_str = str(OutputFactory().generate_sample().dict()).replace("'", '"')

    output_example_str = textwrap.dedent(output_example_str)
    output_example = output_parser.parse(output_example_str)
    output_example_parsed = json.dumps(output_example.dict(), indent=4)

    output_schema = json.loads(output_parser.pydantic_object.schema_json())
    output_schema_parsed = json.dumps(output_schema, indent=4)

    return output_parser, output_schema_parsed, output_example_parsed


def get_objects_table_from_sheets(
    url: str = "https://docs.google.com/spreadsheets/d/122uOaPr8YdW5PTzrxSPF-FD0tgco596HqgB7WK7cHFw/edit#gid=1672006844",
):
    request_url = url.replace("edit#gid=", "export?format=csv&gid=")
    response = requests.get(request_url)
    dataframe = pd.read_csv(io.StringIO(response.content.decode("utf-8")), dtype=str)
    dataframe["label"] = dataframe["label"].fillna("null")
    dataframe = dataframe[dataframe["use"] == "1"]
    dataframe = dataframe.drop(columns=["use"])

    objects_table_md = dataframe.to_markdown(index=False)

    objects_labels = (
        dataframe[["object", "label"]]
        .groupby(by=["object"], sort=False)["label"]
        .apply(lambda x: ", ".join(x))
        .reset_index()
    )
    objects_labels["label"] = objects_labels["label"].str.replace("true, false", "bool")

    objects_labels_md = objects_labels.to_markdown(index=False)
    objects_labels_md = objects_labels_md
    return objects_table_md, objects_labels_md


def get_prompt(prompt_parameters, prompt_template=None, objects_table_md=None):

    if not prompt_template:
        prompt_template = prompt_parameters.get("prompt_text")

    _, output_schema, output_example = get_parser()

    if not objects_table_md:
        objects_table_md = prompt_parameters.get("objects_table_md")

    filled_prompt = (
        prompt_template.replace("                        ", "")
        .replace("{objects_table_md}", objects_table_md)
        .replace("{output_schema}", output_schema)
        .replace("{output_example}", output_example)
    )

    return filled_prompt, prompt_template


class Snapshot(BaseModel):
    object: str
    label_explanation: str
    label: Union[bool, str, None]


class OutputPrediction(BaseModel):
    objects: List[Snapshot]


def get_prediction(
    image_url: str,
    prompt_text: str,
    google_api_model: str,
    max_output_tokens: int,
    temperature: float,
    top_k: int,
    top_p: int,
) -> Dict:

    try:
        image_response = requests.get(image_url)
        model = GenerativeModel(google_api_model)
        responses = model.generate_content(
            contents=[prompt_text, Part.from_data(image_response.content, "image/png")],
            generation_config={
                "max_output_tokens": max_output_tokens,
                "temperature": temperature,
                "top_k": top_k,
                "top_p": top_p,
            },
            safety_settings=SAFETY_CONFIG,
        )

        ai_response = responses.text

    except Exception as exception:
        raise exception

    output_parser = PydanticOutputParser(pydantic_object=OutputPrediction)

    try:
        response_parsed = output_parser.parse(ai_response)
    except Exception as exception:
        raise exception

    return response_parsed.dict()


def explode_df(dataframe, column_to_explode, prefix=None):
    df = dataframe.copy()
    exploded_df = df.explode(column_to_explode)
    new_df = pd.json_normalize(exploded_df[column_to_explode])

    if prefix:
        new_df = new_df.add_prefix(f"{prefix}_")

    df.drop(columns=column_to_explode, inplace=True)
    new_df.index = exploded_df.index
    result_df = df.join(new_df)

    return result_df


# Define a function to handle null values
def calculate_metrics(y_true, y_pred, average):
    # ... (same as before) ...
    # Filter out null values
    valid_indices = y_true.notnull() & y_pred.notnull()
    y_true_filtered = y_true[valid_indices]
    y_pred_filtered = y_pred[valid_indices]

    accuracy = accuracy_score(y_true_filtered, y_pred_filtered)
    precision = precision_score(y_true_filtered, y_pred_filtered, average=average, zero_division=0)
    recall = recall_score(y_true_filtered, y_pred_filtered, average=average, zero_division=0)
    f1 = f1_score(y_true_filtered, y_pred_filtered, average=average, zero_division=0)

    return accuracy, precision, recall, f1


snapshots = [
    {
        "snapshot_id": "https://storage.googleapis.com/datario-public/flooding_detection/classified_images/images_predicted_as_flood/000326_2023-02-13%2021%3A23%3A25.png",
        "ia_identifications": [
            {"object": "image_corrupted", "label": "true"},
            {"object": "road_blockade", "label": "partially"},
            {"object": "water_level", "label": "low"},
            {"object": "rain", "label": "true"},
        ],
        "human_identifications": [
            {"object": "image_corrupted", "label": "true", "count": 10},
            {"object": "image_corrupted", "label": "false", "count": 0},
            {"object": "road_blockade", "label": "partially", "count": 0},
            {"object": "road_blockade", "label": "totally", "count": 0},
            {"object": "road_blockade", "label": "free", "count": 0},
            {"object": "water_level", "label": "low", "count": 0},
            {"object": "water_level", "label": "medium", "count": 0},
            {"object": "water_level", "label": "high", "count": 0},
            {"object": "rain", "label": "true", "count": 0},
            {"object": "rain", "label": "false", "count": 0},
        ],
    },
    {
        "snapshot_id": "https://storage.googleapis.com/datario-public/flooding_detection/classified_images/images_predicted_as_flood/000398_2024-01-13%2023%3A14%3A20.jpeg",
        "ia_identifications": [
            {"object": "image_corrupted", "label": "true"},
            {"object": "road_blockade", "label": "partially"},
            {"object": "water_level", "label": "low"},
            {"object": "rain", "label": "true"},
        ],
        "human_identifications": [
            {"object": "image_corrupted", "label": "true", "count": 0},
            {"object": "image_corrupted", "label": "false", "count": 10},
            {"object": "road_blockade", "label": "partially", "count": 10},
            {"object": "road_blockade", "label": "totally", "count": 0},
            {"object": "road_blockade", "label": "free", "count": 0},
            {"object": "water_level", "label": "low", "count": 0},
            {"object": "water_level", "label": "medium", "count": 10},
            {"object": "water_level", "label": "high", "count": 0},
            {"object": "rain", "label": "true", "count": 10},
            {"object": "rain", "label": "false", "count": 0},
        ],
    },
    {
        "snapshot_id": "https://storage.googleapis.com/datario-public/flooding_detection/classified_images/images_predicted_as_flood/000398_2024-01-14%2001%3A22%3A19.jpeg",
        "ia_identifications": [
            {"object": "image_corrupted", "label": "true"},
            {"object": "road_blockade", "label": "partially"},
            {"object": "water_level", "label": "low"},
            {"object": "rain", "label": "true"},
        ],
        "human_identifications": [
            {"object": "image_corrupted", "label": "true", "count": 0},
            {"object": "image_corrupted", "label": "false", "count": 10},
            {"object": "road_blockade", "label": "partially", "count": 0},
            {"object": "road_blockade", "label": "totally", "count": 10},
            {"object": "road_blockade", "label": "free", "count": 0},
            {"object": "water_level", "label": "low", "count": 0},
            {"object": "water_level", "label": "medium", "count": 0},
            {"object": "water_level", "label": "high", "count": 10},
            {"object": "rain", "label": "true", "count": 10},
            {"object": "rain", "label": "false", "count": 0},
        ],
    },
]


prompt_text_local = """

## Role: Urban Road Image Analyst

#### Expertise and Responsibilities:
As an Expert Urban Road Image Analyst, you specialize in interpreting CCTV images **step by step** to assess various conditions on urban roads. Your expertise includes the detection of image data loss or corruption, as well as analyzing.


#### Key Expertise Areas:
- **Image Data Integrity Analysis:** Expertise in identifying signs of image data loss or corruption, such as uniform grey or green color distortions.
- **Urban Road Condition Assessment:** Proficient in evaluating road conditions and potential hazards unrelated to specific environmental factors.
- **Visual Data Interpretation:** Skilled in analyzing visual data from CCTV images, recognizing patterns and indicators that reflect road conditions and safety issues.

#### Skills:
- **Analytical Prowess:** Exceptional ability to analyze complex visual data, detecting subtle indicators of road-related challenges.
- **Detail-Oriented Observation:** Keen observational skills for identifying minute details in CCTV footage that signify changes in road conditions.


----

### Input

- **Data Provided**: A CCTV image.

### Objects Table

- **Guidance**: Use the table below for object classification, adhering to the specified criteria and identification guides.

{objects_table_md}

### Scenarios examples:

- Example 1: Dry Road with Clear Traffic
```json
{{
    "objects": [
        {{
            "object": "image_corrupted",
            "label_explanation": "Image is clear, no distortion or data loss.",
            "label": "false"
        }},
        {{
            "object": "image_description",
            "label_explanation": "Urban road in daylight with vehicles, clear weather.",
            "label": "null"
        }},
        {{
            "object": "rain",
            "label_explanation": "Road surface is dry, no signs of water.",
            "label": "false"
        }},
        {{
            "object": "water_level",
            "label_explanation": "No water present, road surface completely dry.",
            "label": "low"
        }},
        {{
            "object": "road_blockade",
            "label_explanation": "Road is completely free of obstructions.",
            "label": "free"
        }}
    ]
}}
```

- Example 2: Partially Flooded Road with Moderate Obstructions
```json
{{
    "objects": [
        {{
            "object": "image_corrupted",
            "label_explanation": "Slight blurriness in the image, but generally clear.",
            "label": "true"
        }},
        {{
            "object": "image_description",
            "label_explanation": "Moderate traffic on an urban road with visible puddles.",
            "label": "null"
        }},
        {{
            "object": "rain",
            "label_explanation": "Puddles observed on parts of the road.",
            "label": "true"
        }},
        {{
            "object": "water_level",
            "label_explanation": "Water covers some parts of the road, forming puddles.",
            "label": "medium"
        }},
        {{
            "object": "road_blockade",
            "label_explanation": "Partial obstructions due to water, but traffic can pass.",
            "label": "partially"
        }}
    ]
}}
```

- Example 3: Fully Flooded and Blocked Road
```json
{{
    "objects": [
        {{
            "object": "image_corrupted",
            "label_explanation": "High quality, clear image with no issues.",
            "label": "false"
        }},
        {{
            "object": "image_description",
            "label_explanation": "Road completely submerged in water, no traffic visible.",
            "label": "null"
        }},
        {{
            "object": "rain",
            "label_explanation": "Road is fully covered in water.",
            "label": "true"
        }},
        {{
            "object": "water_level",
            "label_explanation": "Water level high, road completely submerged.",
            "label": "high"
        }},
        {{
            "object": "road_blockade",
            "label_explanation": "Road is entirely blocked by flooding, impassable.",
            "label": "totally"
        }}
    ]
}}
```


### Output

**Output Order**

- **Sequence**: Follow this order in your analysis:
    1. image_corrupted: true or false
    2. image_description: allways null
    3. rain: true or false
    4. water_level: low, medium or high
    5. road_blockade: free, partially or totally

- **Importance**: Adhering to this sequence ensures logical and coherent analysis, with each step informing the subsequent ones.



**Example Format**

- Present findings in a structured JSON format, following the provided example.

```json
{output_example}
```

- **Requirement**: Each label_explanation should be a 500-word interpretation of the image, demonstrating a deep understanding of the visible elements.
- **Important:** Think step by step

"""


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


final_predictions = pd.DataFrame()
for snapshot_id in df["snapshot_id"].unique().tolist():
    snapshot_df = df[df["snapshot_id"] == snapshot_id]
    print(snapshot_id)

    prediction = get_prediction(
        image_url=snapshot_id,
        prompt_text=prompt,
        google_api_model=google_api_model,
        max_output_tokens=max_output_tokens,
        temperature=temperature,
        top_k=top_k,
        top_p=top_p,
    )

    prediction = pd.DataFrame.from_dict(prediction["objects"])
    prediction = prediction[["object", "label", "label_explanation"]].rename(
        columns={"label": "label_ia"}
    )
    final_prediction = snapshot_df.merge(prediction, on="object", how="left")
    final_predictions = pd.concat([final_predictions, final_prediction])


params = {
    # "prompt_template": prompt_text_local,
    # "objects_table_md": objects_table_md,
    "google_api_model": google_api_model,
    "temperature": temperature,
    "top_k": top_k,
    "top_p": top_p,
    "max_output_tokens": max_output_tokens,
}

mlflow.set_tracking_uri(uri="https://mlflow.dados.rio")

# Create a new MLflow Experiment
mlflow.set_experiment("test")

# Start an MLflow run
with mlflow.start_run():
    # Log the hyperparameters
    mlflow.log_params(params)
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
        print(unique_labels)
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
        temp_image_path = f"./data/mlflow/cm_{obj}.png"
        plt.savefig(temp_image_path)

        metrics = {
            f"{obj}_accuracy": accuracy,
            f"{obj}_precision": precision,
            f"{obj}_recall": recall,
            f"{obj}_f1_score": f1,
        }
        mlflow.log_metrics(metrics)
        mlflow.log_artifact(f"./data/mlflow/cm_{obj}.png")
