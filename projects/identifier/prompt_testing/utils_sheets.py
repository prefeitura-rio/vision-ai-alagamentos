# -*- coding: utf-8 -*-
import base64
import hashlib
import json
import os
import time
from collections import OrderedDict
from os import getenv
from pathlib import Path
from typing import List, Union

import gspread
import pandas as pd
from google.oauth2 import service_account


def inject_credential(
    credential_path="/home/jovyan/.basedosdados/credentials/prod.json",
):
    with open(credential_path) as f:
        cred = json.load(f)
    os.environ["GCP_SERVICE_ACCOUNT"] = base64.b64encode(
        str(cred).replace("'", '"').encode("utf-8")
    ).decode("utf-8")


inject_credential(credential_path="/home/jovyan/.basedosdados/credentials/prod.json")


def get_hash_id(string):
    return str(int(hashlib.sha256(string.encode("utf-8")).hexdigest(), 16))[:16]


def get_credentials_from_env(key: str, scopes: List[str] = None) -> service_account.Credentials:
    """
    Gets credentials from env vars
    """
    env: str = getenv(key, "")
    if env == "":
        raise ValueError(f'Enviroment variable "{key}" not set!')
    info: dict = json.loads(base64.b64decode(env))
    cred: service_account.Credentials = service_account.Credentials.from_service_account_info(info)
    if scopes:
        cred = cred.with_scopes(scopes)
    return cred


def get_gspread_sheet(
    sheet_url: str, google_sheet_credential_env_name: str = "GCP_SERVICE_ACCOUNT"
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
    google_sheet_credential_env_name: str = "GCP_SERVICE_ACCOUNT",
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
    google_sheet_credential_env_name: str = "GCP_SERVICE_ACCOUNT",
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
    google_sheet_credential_env_name: str = "GCP_SERVICE_ACCOUNT",
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
    content_url: str = None,
    google_sheet_credential_env_name: str = "GCP_SERVICE_ACCOUNT",
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
                "content"            : List[dict],
                "image_url"          : str,
                "image"              : str,
            }
        data_url: str
        google_sheet_credential_env_name: str

    """
    if not save_data:
        return None

    gspread_sheet = get_gspread_sheet(
        sheet_url=data_url or content_url,
        google_sheet_credential_env_name=google_sheet_credential_env_name,
    )
    #################################################################
    # Save Content Prompts
    content_id = ""
    if content_url is not None:
        content_gid = int(content_url.split("gid=")[-1])
        content_worksheet = gspread_sheet.get_worksheet_by_id(content_gid)
        content_ids = content_worksheet.get_values("A:A")
        if content_ids != []:
            dataframe = pd.DataFrame(content_ids)
            new_header = dataframe.iloc[0]  # grab the first row for the header
            dataframe = dataframe[1:]  # take the data less the header row
            dataframe.columns = new_header  # set the header row as the df header
            content_ids = dataframe["content_id"].tolist()

        # content_parsed = []
        # for d in data.get("content"):
        #     new_d = {}
        #     for key, value in d.items():
        #         new_d[key] = json.dumps(value, indent=4)
        #     content_parsed.append(new_d)

        content_str = json.dumps(data.get("content"), indent=4)
        content_str_id = (
            content_str
            + "__"
            + str(data.get("max_output_token", ""))
            + "__"
            + str(data.get("temperature", ""))
            + "__"
            + str(data.get("top_k", ""))
            + "__"
            + str(data.get("top_p", ""))
        )
        content_id = get_hash_id(string=content_str_id)

        if content_id not in content_ids:
            sheet_append_row(
                worksheet=content_worksheet,
                data_dict={
                    "content_id": content_id,
                    "content": content_str,
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
            "content_id": content_id,
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
