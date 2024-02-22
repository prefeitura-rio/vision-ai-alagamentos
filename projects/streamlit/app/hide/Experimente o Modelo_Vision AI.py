# -*- coding: utf-8 -*-
from utils.model import run_model

import streamlit as st

MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB

st.set_page_config(layout="wide", page_title="Experimente o Modelo")
st.image("./data/logo/logo.png", width=300)

st.markdown("# Identifique um alagamento por uma imagem")

my_upload = st.file_uploader("Faça upload de uma imagem", type=["png", "jpg", "jpeg"])

prompt = st.text_area(
    label="add a prompt to the model (optional)",
    value="""
                You are an expert flooding detector.

                You are given a image. You must detect if there is flooding in the image.

                the output MUST be a json object with a boolean value for the key "flooding_detected".

                If you don't know what to anwser, you can set the key "flooding_detect" as false.

                Example:
                {
                    "flooding_detected": true
                }
    """,
)

prompt

if my_upload is not None:
    if my_upload.size > MAX_FILE_SIZE:
        st.error("The uploaded file is too large. Please upload an image smaller than 5MB.")
    else:
        res = run_model(my_upload, prompt=prompt)
else:
    my_upload = "./data/imgs/flooded1.jpg"
    res = run_model(my_upload, prompt=prompt)

if res:
    st.markdown("### Alagamento Identificado ✅")
else:
    st.markdown("### Alagamento Não Identificado ❌")

st.image(my_upload)
