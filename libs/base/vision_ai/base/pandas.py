# -*- coding: utf-8 -*-
import pandas as pd


def explode_df(dataframe: pd.DataFrame, column_to_explode: str, prefix: str = None):
    df = dataframe.copy()
    exploded_df = df.explode(column_to_explode)
    new_df = pd.json_normalize(exploded_df[column_to_explode])

    if prefix:
        new_df = new_df.add_prefix(f"{prefix}_")

    df.drop(columns=column_to_explode, inplace=True)
    new_df.index = exploded_df.index
    result_df = df.join(new_df)

    return result_df


def handle_snapshots_df(
    snapshots: pd.DataFrame, human_identification_col: str = "human_identification"
) -> pd.DataFrame:
    # Explode human_identification column
    snapshots_exploded = snapshots.explode(human_identification_col)

    # Extract labels and counts
    snapshots_exploded["label"] = snapshots_exploded[human_identification_col].apply(
        lambda x: x["label"]
    )
    snapshots_exploded["object"] = snapshots_exploded[human_identification_col].apply(
        lambda x: x["object"]
    )
    snapshots_exploded["count"] = snapshots_exploded[human_identification_col].apply(
        lambda x: x["count"]
    )

    # Group by object and calculate label distribution
    snapshots_exploded.dropna(subset=["label"], inplace=True)
    snapshots_exploded.query("label != 'null'", inplace=True)
    grouped = (
        snapshots_exploded.groupby(
            ["snapshot_id", "snapshot_timestamp", "snapshot_url", "object", "label"]
        )["count"]
        .sum()
        .reset_index()
    )
    grouped["distribution"] = grouped.groupby("object")["count"].transform(lambda x: x)

    # Aggregate labels and distributions for each object
    result = (
        grouped.groupby(["snapshot_id", "snapshot_timestamp", "snapshot_url", "object"])[
            ["label", "distribution"]
        ]
        .agg(list)
        .reset_index()
    )

    # Get hard label using the highest probability
    result["hard_label"] = result.apply(
        lambda x: x["label"][x["distribution"].index(max(x["distribution"]))], axis=1
    )

    # Get count for hard label
    result["count"] = result.apply(lambda x: max(x["distribution"]), axis=1)

    # Normalize distribution
    result["distribution"] = result["distribution"].apply(
        lambda x: [round(i / sum(x), 2) for i in x]
    )

    return result


def get_objetcs_labels_df(objects: pd.DataFrame, keep_null: bool = True):
    objects_df = objects.rename(columns={"id": "object_id"})
    objects_df = objects_df[["name", "object_id", "labels"]]
    labels = explode_df(objects_df, "labels")
    if not keep_null:
        labels = labels[~labels["value"].isin(["null"])]
    labels = labels.rename(columns={"label_id": "label"})
    labels = labels.reset_index(drop=True)

    mask = (labels["value"] == "null") & (labels["name"] != "image_description")  # noqa
    labels = labels[~mask]

    selected_labels_cols = ["name", "criteria", "identification_guide", "value", "text"]
    labels = labels[selected_labels_cols]
    labels = labels.rename(columns={"name": "object", "value": "label"})
    return labels


def get_prompt_objects_df(labels_df: pd.DataFrame, prompt_objects: list):
    objects_df = pd.DataFrame()
    for obj in prompt_objects:
        obj_labels_df = labels_df[labels_df["object"] == obj]
        obj_labels_df = obj_labels_df.sort_values("label")
        objects_df = pd.concat([objects_df, obj_labels_df])

    return objects_df
