# -*- coding: utf-8 -*-
import json

import pandas as pd
import streamlit as st
from utils.utils import (
    get_objects,
    get_objects_cache,
    get_objetcs_labels_df,
    get_prompts,
    get_prompts_cache,
)

st.set_page_config(page_title="Visualizar Prompt", layout="wide", initial_sidebar_state="collapsed")
# st.image("./data/logo/logo.png", width=300)

st.markdown("# Visualizar Prompt | Vision AI")


# Function to fetch and update data
def fetch_and_update_prompts(bypass_cash=False):
    if bypass_cash:
        return get_prompts()
    return get_prompts_cache()


def fetch_and_update_objects(bypass_cash=False):
    if bypass_cash:
        return get_objects()
    return get_objects_cache()


prompt_data = fetch_and_update_prompts()
objects_data = fetch_and_update_objects()

# Add a button for updating data
if st.button("Update Data"):
    prompt_data = fetch_and_update_prompts(bypass_cash=True)
    objects_data = fetch_and_update_objects(bypass_cash=True)
    st.success("Data updated successfully!")

objects = pd.DataFrame(objects_data)
labels = get_objetcs_labels_df(objects, keep_null=True)

prompt_parameters = prompt_data[0]
prompt_text = prompt_parameters.get("prompt_text")
prompt_objects = prompt_parameters.get("objects")


selected_labels_cols = ["name", "criteria", "identification_guide", "value"]
labels = labels[selected_labels_cols]
labels = labels[labels["name"].isin(prompt_objects)]
labels = labels.rename(columns={"name": "object", "value": "label"})
objects_table_md = labels.to_markdown(index=False)


output_schema = """{\n    "$defs": {\n        "Object": {\n            "properties": {\n                "object": {\n"description": "The object from the objects table",\n"title": "Object",\n"type": "string"\n                },\n                "label_explanation": {\n"description": "Highly detailed visual description of the image given the object context",\n"title": "Label Explanation",\n"type": "string"\n                },\n                "label": {\n"anyOf": [\n    {\n        "type": "boolean"\n    },\n    {\n        "type": "string"\n    },\n    {\n        "type": "null"\n    }\n],\n"description": "Label indicating the condition or characteristic of the object",\n"title": "Label"\n                }\n            },\n            "required": [\n                "object",\n                "label_explanation",\n                "label"\n            ],\n            "title": "Object",\n            "type": "object"\n        }\n    },\n    "properties": {\n        "objects": {\n            "items": {\n                "$ref": "#/$defs/Object"\n            },\n            "title": "Objects",\n            "type": "array"\n        }\n    },\n    "required": [\n        "objects"\n    ],\n    "title": "Output",\n    "type": "object"\n}\n"""  # noqa
output_schema = json.dumps(json.loads(output_schema), indent=4)
output_example = """{\n    "objects": [\n        {\n            "object": "<Object from objects table>",\n            "label_explanation": "<Visual description of the image given the object context>",\n            "label": "<Selected label from objects table>"\n        }\n    ]\n}\n"""  # noqa
output_example = json.dumps(json.loads(output_example), indent=4)

prompt_text = (
    prompt_text.replace("{objects_table_md}", objects_table_md)
    .replace("{output_schema}", output_schema)
    .replace("{output_example}", output_example)
)
st.markdown(prompt_text)
