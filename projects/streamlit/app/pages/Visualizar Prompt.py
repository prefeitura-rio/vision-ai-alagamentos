# -*- coding: utf-8 -*-
import streamlit as st
from utils.utils import get_objects, get_objects_cache, get_prompts, get_prompts_cache
from vision_ai.base.prompt import get_prompt_api

# Set page config
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


prompt, objects_table = get_prompt_api(
    prompt_name="base", prompt_data=prompt_data, objects_data=objects_data
)
st.markdown(prompt)
