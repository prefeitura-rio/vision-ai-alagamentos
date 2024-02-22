# -*- coding: utf-8 -*-
from vision_ai.base.shared_models import get_parser


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
