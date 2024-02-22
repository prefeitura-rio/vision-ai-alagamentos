# -*- coding: utf-8 -*-
import json
from typing import Optional

from google.cloud import bigquery
from vision_ai.base.utils import get_datetime


def save_data_in_bq(
    project_id: str,
    dataset_id: str,
    table_id: str,
    json_data: dict,
    error_step: Optional[str] = None,
    ai_response_parsed: Optional[str] = None,
    ai_response: Optional[str] = None,
    error_message: Optional[str] = None,
    error_name: Optional[str] = None,
) -> None:
    client = bigquery.Client()
    table_full_name = f"{project_id}.{dataset_id}.{table_id}"

    schema = [
        bigquery.SchemaField("camera_id", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("data_particao", "DATE", mode="NULLABLE"),
        bigquery.SchemaField("start_datetime", "DATETIME", mode="NULLABLE"),
        bigquery.SchemaField("end_datetime", "DATETIME", mode="NULLABLE"),
        bigquery.SchemaField("ai_input", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("ai_response_parsed", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("ai_response", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("error_step", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("error_name", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("error_message", "STRING", mode="NULLABLE"),
    ]

    job_config = bigquery.LoadJobConfig(
        schema=schema,
        # Optionally, set the write disposition. BigQuery appends loaded rows
        # to an existing table by default, but with WRITE_TRUNCATE write
        # disposition it replaces the table with the loaded data.
        write_disposition="WRITE_APPEND",
        time_partitioning=bigquery.TimePartitioning(
            type_=bigquery.TimePartitioningType.DAY,
            field="data_particao",  # name of column to use for partitioning
        ),
    )

    end_datetime = get_datetime()
    json_data["end_datetime"] = end_datetime
    json_data["ai_response_parsed"] = ai_response_parsed
    json_data["ai_response"] = ai_response
    json_data["error_step"] = error_step
    json_data["error_name"] = error_name
    json_data["error_message"] = error_message

    json_data = json.loads(json.dumps([json_data]))
    try:
        job = client.load_table_from_json(
            json_data, table_full_name, job_config=job_config
        )
        job.result()
    except Exception:
        raise Exception(json_data)
