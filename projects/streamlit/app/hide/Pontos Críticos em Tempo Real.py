# -*- coding: utf-8 -*-
import folium
import pandas as pd
import requests
from streamlit_folium import st_folium

import streamlit as st

st.set_page_config(layout="wide", page_title="Pontos Críticos em Tempo Real")
st.image("./data/logo/logo.png", width=300)


def create_map(chart_data):
    chart_data = chart_data.fillna("")
    # center map on the mean of the coordinates
    if len(chart_data) > 0:
        m = folium.Map(
            location=[chart_data["latitude"].mean(), chart_data["longitude"].mean()],
            zoom_start=11,
        )
    else:
        m = folium.Map(location=[-22.917690, -43.413861], zoom_start=11)

    for i in range(0, len(chart_data)):
        folium.Marker(
            location=[chart_data.iloc[i]["latitude"], chart_data.iloc[i]["longitude"]],
            # add nome_da_camera and status to tooltip
            tooltip=f"""
            {chart_data.iloc[i]['status_emoji']}  {chart_data.iloc[i]['status_15min']}<br>
            {chart_data.iloc[i]['endereco']}<br>
            {chart_data.iloc[i]['Detalhe']}""",
            # change icon color according to status
            icon=folium.features.DivIcon(
                icon_size=(15, 15),
                icon_anchor=(7, 7),
                html=f'<div style="width: 10px; height: 10px; background-color: {chart_data.iloc[i]["color"]}; border: 1px solid black; border-radius: 50%;"></div>',  # noqa
            ),
        ).add_to(m)

    return m


@st.cache_data(ttl=60)
def load_pontos_criticos():
    return pd.read_csv("data/database/pontos_criticos.csv")


@st.cache_data(ttl=60)
def load_precipitacao():
    precipitacao_15min = pd.read_json(
        "https://api.dados.rio/v2/clima_pluviometro/precipitacao_15min/"
    )[["id_h3", "chuva_15min", "status", "color"]].rename(columns={"status": "status_15min"})
    precipitacao_120min = pd.read_json(
        "https://api.dados.rio/v2/clima_pluviometro/precipitacao_120min/"
    )[["id_h3", "chuva_15min", "status"]].rename(
        columns={"chuva_15min": "chuva_120min", "status": "status_120min"}
    )

    return pd.merge(precipitacao_120min, precipitacao_15min, on="id_h3")


# Define a function to map status to emoji
def status_to_emoji(status):
    if status == "chuva forte":
        return "🔴"
    elif status == "chuva moderada":
        return "🟠"
    elif status == "chuva muito forte":
        return "🟣"
    else:
        return "🟢"


# Define a function to map status to color code
def status_to_color(status):
    if status == "chuva forte":
        return "#FF0000"  # red
    elif status == "chuva moderada":
        return "#FF8C00"  # yellow
    elif status == "chuva muito forte":
        return "#800080"  # purple
    else:
        return "#008000"  # green


# @st.cache_data()
def update_precipitacao():
    """Add precipitation data to pontos_criticos DataFrame. Always update the precipitation data."""

    df = load_pontos_criticos()
    precipitacao = load_precipitacao()

    # Drop the existing columns in pontos_criticos that are also in precipitacao
    # expect h3_id
    df.drop(
        columns=[col for col in df.columns if col in precipitacao.columns and col != "id_h3"],
        inplace=True,
    )

    # Merge the dataframes, replacing the precipitation data in pontos_criticos
    df_merge = pd.merge(df, precipitacao, on="id_h3", how="left")

    # Add a new column with emojis
    df_merge["status_emoji"] = df_merge["status_15min"].apply(status_to_emoji)

    # Add a new column with color codes
    df_merge["color"] = df_merge["status_15min"].apply(status_to_color)

    return df_merge


@st.cache_data(ttl=60)
def get_apis_last_updates():
    last_updates = [
        {
            "alagamento_ia": pd.to_datetime(
                requests.get(
                    "https://api.dados.rio/v2/clima_alagamento/ultima_atualizacao_alagamento_detectado_ia/"
                ).text.strip('"')
            ),
            "precipitacao_15min": pd.to_datetime(
                requests.get(
                    "https://api.dados.rio/v2/clima_pluviometro/ultima_atualizacao_precipitacao_15min/"
                ).text.strip('"'),
                dayfirst=True,
            ),
            "precipitacao_120min": pd.to_datetime(
                requests.get(
                    "https://api.dados.rio/v2/clima_pluviometro/ultima_atualizacao_precipitacao_120min/"
                ).text.strip('"'),
                dayfirst=True,
            ),
        }
    ]
    return pd.DataFrame(last_updates).T.rename(columns={0: "Última Atualização"})


# #### FRONTEND ####


st.sidebar.dataframe(get_apis_last_updates())

st.markdown("### Acompanhe os Pontos Críticos em Tempo Real")

pontos_criticos = update_precipitacao()

# Tabela com pontos de atenção
st.dataframe(
    pontos_criticos[
        [
            "status_emoji",
            "bairro",
            "endereco",
            "status_15min",
            "status_120min",
            "chuva_15min",
            "chuva_120min",
        ]
    ].sort_values(by=["chuva_15min"], ascending=False),
    column_config={
        "status_emoji": st.column_config.Column(
            "",
        ),
        "bairro": st.column_config.Column(
            "Bairro",
            help="Bairro",
            # width="medium",
            required=True,
        ),
        "endereco": st.column_config.Column(
            "Endereço",
            help="Endereço aproximado",
            # width="medium",
            required=True,
        ),
        "status_15min": st.column_config.Column(
            "Status 15 min",
            help="Status da precipitação nos últimos 15 minutos",
            # width="medium",
            required=True,
        ),
        "chuva_15min": st.column_config.Column(
            "Acumulado 15 min",
            help="Precipitação acumulada nos últimos 15 minutos",
            # width="medium",
            required=True,
        ),
        "status_120min": st.column_config.Column(
            "Status 120 min",
            help="Status da precipitação nos últimos 120 minutos",
            # width="medium",
            # required=True,
        ),
        "chuva_120min": st.column_config.Column(
            "Acumulado 120 min",
            help="Precipitação acumulada nos últimos 120 minutos",
            # width="medium",
            # required=True,
        ),
    },
    hide_index=True,
    use_container_width=True,
)

# # Mapa
# folium_map = create_map(pontos_criticos)  # replace with your map generation code

folium_map = create_map(pontos_criticos)
# call to render Folium map in Streamlit
map_data = st_folium(
    folium_map,
    key="fig1",
    height=600,
    width=1200,
    # returned_objects=["last_object_clicked"],
)

# # select pontos_criticos obj based on last_object_clicked coordinates
obj_coord = map_data["last_object_clicked"]

# # info adicional quando objeto é clicado
if obj_coord is None:
    st.write("Clique em um marcador para ver os detalhes")
else:
    selected_data = pontos_criticos[
        (pontos_criticos["latitude"] == obj_coord["lat"])
        & (pontos_criticos["longitude"] == obj_coord["lng"])
    ]

    selected_data = (
        selected_data[["endereco", "Detalhe", "Obs", "Status"]]
        # .rename(
        #     columns={
        #         "id_camera": "Identificador",
        #         "url_camera": "🎥 Camera",
        #     }
        # )
        .T
    )
    selected_data.columns = ["Infos"]

    #     #     st.markdown("### 📷 Imagem da Câmera")
    #     #     st.image(generate_image(image_b64))

    selected_data
