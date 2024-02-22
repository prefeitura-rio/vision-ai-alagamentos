# -*- coding: utf-8 -*-
import pandas as pd
import requests
import streamlit as st

st.set_page_config(layout="wide", page_title="Pontos de Alagamento")
st.image("./data/logo/logo.png", width=300)

st.markdown("# Pontos de Alagamento | Vision AI")


@st.cache_data(ttl=60)
def load_alagamento_detectado_ia():
    raw_api_data = requests.get(
        "https://api.dados.rio/v2/clima_alagamento/alagamento_detectado_ia/"
    ).json()
    last_update = pd.to_datetime(
        requests.get(
            "https://api.dados.rio/v2/clima_alagamento/ultima_atualizacao_alagamento_detectado_ia/"
        ).text.strip('"')
    )

    dataframe = pd.json_normalize(
        raw_api_data,
        record_path="ai_classification",
        meta=[
            "datetime",
            "id_camera",
            "url_camera",
            "latitude",
            "longitude",
            "image_url",
        ],
    )

    # filter only flooded cameras
    dataframe = dataframe[dataframe["label"] == True]  # noqa

    return dataframe, last_update


chart_data, last_update = load_alagamento_detectado_ia()

if len(chart_data) > 0:
    # Display images in a grid
    num_columns = 2
    num_rows = (len(chart_data) + num_columns - 1) // num_columns

    for row in range(num_rows):
        cols = st.columns(num_columns)
        for col in range(num_columns):
            index = row * num_columns + col
            if index < len(chart_data):
                with cols[col]:
                    st.subheader(f"Camera ID: {chart_data.iloc[index]['id_camera']}")
                    st.write(f"Last Update: {last_update}")
                    st.image(chart_data.iloc[index]["image_url"], use_column_width=True)
else:
    st.markdown("Não foi identificado nenhum ponto de alagamento.")
