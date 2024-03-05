# -*- coding: utf-8 -*-
import json

import pandas as pd
from vision_ai.base.pandas import get_objetcs_labels_df, get_prompt_objects_df
from vision_ai.base.shared_models import get_parser


def get_prompt_local(prompt_parameters, prompt_template=None, objects_table_md=None):
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


def get_prompt_api(prompt_name: str = "base", prompt_data: list = None, objects_data: list = None):
    for prompt in prompt_data:
        if prompt.get("name") == prompt_name:
            prompt_parameters = prompt

    prompt_text = prompt_parameters.get("prompt_text")
    prompt_objects = prompt_parameters.get("objects")

    labels_df = get_objetcs_labels_df(objects=pd.DataFrame(objects_data), keep_null=True)
    objects_table = get_prompt_objects_df(
        labels_df=labels_df,
        prompt_objects=prompt_objects,
    )
    objects_table_md = objects_table.to_markdown(index=False)

    _, output_schema_parsed, output_example_parsed = get_parser()
    output_schema = json.dumps(json.loads(output_schema_parsed), indent=4)
    output_example = json.dumps(json.loads(output_example_parsed), indent=4)

    prompt_text = (
        prompt_text.replace("{objects_table_md}", objects_table_md)
        .replace("{output_schema}", output_schema)
        .replace("{output_example}", output_example)
    )
    prompt_parameters["prompt_text"] = prompt_text
    return prompt_parameters, objects_table
