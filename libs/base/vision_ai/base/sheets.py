# -*- coding: utf-8 -*-
# -*- coding: utf-8 -*-
import base64
import hashlib
import io
import json
import os
import time
from collections import OrderedDict
from os import getenv
from pathlib import Path
from typing import List, Union

import gspread
import pandas as pd
import requests
from google.oauth2 import service_account


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


def inject_credential(
    credential_path="/home/jovyan/.basedosdados/credentials/prod.json",
):
    with open(credential_path) as f:
        cred = json.load(f)
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = base64.b64encode(
        str(cred).replace("'", '"').encode("utf-8")
    ).decode("utf-8")


def get_hash_id(string):
    return str(int(hashlib.sha256(string.encode("utf-8")).hexdigest(), 16))[:16]


def get_credentials_from_env(key: str, scopes: List[str] = None) -> service_account.Credentials:
    """
    Gets credentials from env vars
    """
    env: str = getenv(key, "")
    if env == "":
        raise ValueError(f'Enviroment variable "{key}" not set!')
    try:
        info: dict = json.loads(base64.b64decode(env))
    except:
        info: dict = json.load(open(env, "r"))
    cred: service_account.Credentials = service_account.Credentials.from_service_account_info(info)
    if scopes:
        cred = cred.with_scopes(scopes)
    return cred


def get_gspread_sheet(
    sheet_url: str, google_sheet_credential_env_name: str = "GOOGLE_APPLICATION_CREDENTIALS"
) -> gspread.Client:
    url_prefix = "https://docs.google.com/spreadsheets/d/"
    if not sheet_url.startswith(url_prefix):
        raise ValueError(
            "URL must start with https://docs.google.com/spreadsheets/d/"
            f"Invalid URL: {sheet_url}"
        )
    credentials = get_credentials_from_env(
        key=google_sheet_credential_env_name,
        scopes=[
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive",
        ],
    )
    gspread_client = gspread.authorize(credentials)
    sheet = gspread_client.open_by_url(sheet_url)
    time.sleep(1.5)
    return sheet


def sheet_append_row(
    worksheet: gspread.worksheet,
    data_dict: dict,
):
    first_row = worksheet.get_values("A1:Z1")
    data_rows = list(data_dict.keys())

    if first_row != []:
        new_first_row = []
        for column in first_row[0]:
            if column in data_rows:
                new_first_row.append(column)
        # order dict in the same order as the header
        ordered_data = OrderedDict((key, data_dict[key]) for key in new_first_row)
    else:
        header = list(data_dict.keys())
        # append header
        worksheet.append_row(header)
        ordered_data = data_dict

    save_data_values = list(ordered_data.values())
    worksheet.append_row(save_data_values, value_input_option="USER_ENTERED")
    time.sleep(1.5)


def get_sheet_data(
    gsheets_url: str,
    google_sheet_credential_env_name: str = "GOOGLE_APPLICATION_CREDENTIALS",
    N: int = 10,
):
    gspread_sheet = get_gspread_sheet(
        sheet_url=gsheets_url,
        google_sheet_credential_env_name=google_sheet_credential_env_name,
    )

    gid = int(gsheets_url.split("gid=")[-1])
    worksheet = gspread_sheet.get_worksheet_by_id(gid)

    dataframe = pd.DataFrame(worksheet.get_values())
    new_header = dataframe.iloc[0]  # grab the first row for the header
    dataframe = dataframe[1:]  # take the data less the header row
    dataframe.columns = new_header  # set the header row as the df header

    return dataframe


def get_sessions_from_sheets(
    gsheets_url: str,
    google_sheet_credential_env_name: str = "GOOGLE_APPLICATION_CREDENTIALS",
    N: int = 10,
):
    dataframe = get_sheet_data(
        gsheets_url=gsheets_url,
        google_sheet_credential_env_name=google_sheet_credential_env_name,
        N=N,
    )
    sessions = []
    for session_id in dataframe["session_id"].unique():
        df_session = dataframe[dataframe["session_id"] == session_id].fillna("")
        cols = ["session_id", "message", "true_label"]
        sessions.append(df_session[cols].to_dict(orient="records"))
    return sessions


def get_knowledge_base_from_sheets(
    gsheets_url: str,
    google_sheet_credential_env_name: str = "GOOGLE_APPLICATION_CREDENTIALS",
    N: int = 10,
):
    dataframe = get_sheet_data(
        gsheets_url=gsheets_url,
        google_sheet_credential_env_name=google_sheet_credential_env_name,
        N=N,
    )
    return dataframe.to_dict(orient="records")


def save_json_knowledge_base(
    save_path: Union[str, Path] = "./train/services_knowledge_json",
    data: List[dict] = [{}],
):
    save_path = Path(save_path)
    if not save_path.exists():
        save_path.mkdir(parents=True, exist_ok=True)
    for service in data:
        flow_id = service.get("flow-id", None)
        if flow_id is None:
            raise ValueError("Data `flow_id` is required")
        else:
            service["descricao"] = service["descricao"].replace("\n", " ", 1).strip()

            file_path = save_path / str(flow_id + ".json")
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(service, f, ensure_ascii=False, indent=4)


def save_data_in_sheets(
    save_data: bool = False,
    data: dict = {},
    data_url: str = None,
    prompt_url: str = None,
    google_sheet_credential_env_name: str = "GOOGLE_APPLICATION_CREDENTIALS",
):
    """
    Saves data to a google sheet.

    Parameters
        data:
            {
                "experiment_name"    : str,
                "experiment_datetime": str,
                "object"             : str,
                "explanation"        : str,
                "prompt"            : List[dict],
                "image_url"          : str,
                "image"              : str,
            }
        data_url: str
        google_sheet_credential_env_name: str

    """

    if not save_data:
        return None

    gspread_sheet = get_gspread_sheet(
        sheet_url=data_url or prompt_url,
        google_sheet_credential_env_name=google_sheet_credential_env_name,
    )
    #################################################################
    # Save prompt Prompts
    prompt_id = ""
    if prompt_url is not None:
        prompt_gid = int(prompt_url.split("gid=")[-1])
        prompt_worksheet = gspread_sheet.get_worksheet_by_id(prompt_gid)
        prompt_ids = prompt_worksheet.get_values("A:A")
        if prompt_ids != []:
            dataframe = pd.DataFrame(prompt_ids)
            new_header = dataframe.iloc[0]  # grab the first row for the header
            dataframe = dataframe[1:]  # take the data less the header row
            dataframe.columns = new_header  # set the header row as the df header
            prompt_ids = dataframe["prompt_id"].tolist()

        # prompt_parsed = []
        # for d in data.get("prompt"):
        #     new_d = {}
        #     for key, value in d.items():
        #         new_d[key] = json.dumps(value, indent=4)
        #     prompt_parsed.append(new_d)

        prompt_str = json.dumps(data.get("prompt"), indent=4)
        prompt_str_id = (
            prompt_str
            + "__"
            + str(data.get("max_output_token", ""))
            + "__"
            + str(data.get("temperature", ""))
            + "__"
            + str(data.get("top_k", ""))
            + "__"
            + str(data.get("top_p", ""))
        )
        prompt_id = get_hash_id(string=prompt_str_id)

        if prompt_id not in prompt_ids:
            sheet_append_row(
                worksheet=prompt_worksheet,
                data_dict={
                    "prompt_id": prompt_id,
                    "prompt": prompt_str,
                    "max_output_token": data.get("max_output_token", ""),
                    "temperature": data.get("temperature", ""),
                    "top_k": data.get("top_k", ""),
                    "top_p": data.get("top_p", ""),
                },
            )
    if data_url is not None:
        save_data = {
            "experiment_name": data.get("experiment_name", ""),
            "experiment_datetime": data.get("experiment_datetime", ""),
            "prompt_id": prompt_id,
            "true_object": data.get("true_object", ""),
            "response": json.dumps(data.get("response", ""), indent=4),
            "image_url": data.get("image_url", ""),
            "image": data.get("image", ""),
        }
        data_gid = int(data_url.split("gid=")[-1])
        data_worksheet = gspread_sheet.get_worksheet_by_id(data_gid)
        sheet_append_row(
            worksheet=data_worksheet,
            data_dict=save_data,
        )

        return data_worksheet


def create_google_sheet_from_dataframe(
    df: pd.DataFrame,
    sheet_title: str,
    worksheet_title: str,
    google_sheet_credential_env_name: str = "GOOGLE_APPLICATION_CREDENTIALS",
):
    """
    Creates a Google Sheet from a Pandas DataFrame.

    Parameters:
        df (pd.DataFrame): The DataFrame to be exported to Google Sheets.
        sheet_title (str): The title of the new Google Sheet.
        google_sheet_credential_env_name (str): Environment variable name for Google Sheets credentials.
    """
    # Authenticate and create the sheet
    credentials = get_credentials_from_env(
        key=google_sheet_credential_env_name,
        scopes=[
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive",
        ],
    )
    gspread_client = gspread.authorize(credentials)
    try:
        sheet = gspread_client.open(sheet_title)
    except gspread.SpreadsheetNotFound:
        sheet = gspread_client.create(sheet_title)

    # Open the first worksheet
    worksheet = sheet.add_worksheet(title=worksheet_title, rows=1000, cols=20)

    if "snapshot_url" in df:
        df["snapshot_url"] = df["snapshot_url"].apply(
            lambda url: f'=IMAGE("{url}")' if pd.notna(url) else ""
        )

    # Convert DataFrame to list of lists (each row becomes a list)
    df = df.astype(str)
    data = df.values.tolist()

    # Add the DataFrame to sheet
    worksheet.update(
        "A1", [df.columns.values.tolist()] + data, value_input_option="USER_ENTERED"
    )  # Adds the header and data

    # Make the sheet public
    sheet.share(None, perm_type="anyone", role="writer")

    return sheet.url
