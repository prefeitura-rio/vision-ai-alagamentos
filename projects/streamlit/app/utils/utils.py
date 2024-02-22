# -*- coding: utf-8 -*-
import json  # noqa
import os  # noqa
from typing import Union

import folium
import pandas as pd
import streamlit as st
from st_aggrid import GridOptionsBuilder  # noqa
from st_aggrid import GridUpdateMode  # noqa
from st_aggrid import AgGrid, ColumnsAutoSizeMode  # noqa
from utils.api import APIVisionAI

TRADUTOR = {
    "image_corrupted": "imagem corrompida",
    "image_description": "descrição da imagem",
    "rain": "chuva",
    "water_level": "nível da água",
    "traffic": "tráfego",
    "road_blockade": "bloqueio de estrada",
    "false": "falso",
    "true": "verdadeiro",
    "null": "nulo",
    "low": "baixo",
    "medium": "médio",
    "high": "alto",
    "easy": "fácil",
    "moderate": "moderado",
    "difficult": "difícil",
    "impossible": "impossível",
    "free": "livre",
    "partially": "parcialmente",
    "totally": "totalmente",
}


def get_vision_ai_api():
    def user_is_logged_in():
        if "logged_in" not in st.session_state:
            st.session_state["logged_in"] = False

        def callback_data():
            username = st.session_state["username"]
            password = st.session_state["password"]
            try:
                _ = APIVisionAI(
                    username=username,
                    password=password,
                )
                st.session_state["logged_in"] = True
            except Exception as exc:
                st.error(f"Error: {exc}")
                st.session_state["logged_in"] = False

        if st.session_state["logged_in"]:
            return True

        st.write("Please login")
        st.text_input("Username", key="username")
        st.text_input("Password", key="password", type="password")
        st.button("Login", on_click=callback_data)
        return False

    if not user_is_logged_in():
        st.stop()

    vision_api = APIVisionAI(
        username=st.session_state["username"],
        password=st.session_state["password"],
    )
    return vision_api


vision_api = get_vision_ai_api()
# vision_api = APIVisionAI(
#     username=os.environ.get("VISION_API_USERNAME"),
#     password=os.environ.get("VISION_API_PASSWORD"),
# )


def get_cameras(
    only_active=True,
    use_mock_data=False,
    update_mock_data=False,
    page_size=3000,
    timeout=120,
):
    mock_data_path = "./data/temp/mock_api_data.json"

    if use_mock_data:
        with open(mock_data_path) as f:
            data = json.load(f)
        return data
    if only_active:
        cameras_ativas = vision_api._get_all_pages(
            "/agents/89173394-ee85-4613-8d2b-b0f860c26b0f/cameras"
        )
        cameras_ativas_ids = [f"/cameras/{d.get('id')}" for d in cameras_ativas]  # noqa
        data = vision_api._get_all_pages(cameras_ativas_ids, timeout=timeout)
    else:
        data = vision_api._get_all_pages(path="/cameras", page_size=page_size, timeout=timeout)

    if update_mock_data:
        with open(mock_data_path, "w") as f:
            json.dump(data, f)

    return data


def get_objects(
    page_size=100,
    timeout=120,
):
    data = vision_api._get_all_pages(path="/objects", page_size=page_size, timeout=timeout)
    return data


def get_prompts(
    page_size=100,
    timeout=120,
):
    data = vision_api._get_all_pages(path="/prompts", page_size=page_size, timeout=timeout)
    return data


@st.cache_data(ttl=60 * 2, persist=False)
def get_cameras_cache(
    only_active=True,
    use_mock_data=False,
    update_mock_data=False,
    page_size=3000,
    timeout=120,
):
    return get_cameras(
        only_active=only_active,
        use_mock_data=use_mock_data,
        update_mock_data=update_mock_data,
        page_size=page_size,
        timeout=timeout,
    )


@st.cache_data(ttl=60 * 2, persist=False)
def get_objects_cache(page_size=100, timeout=120):
    return get_objects(page_size=page_size, timeout=timeout)


@st.cache_data(ttl=60 * 2, persist=False)
def get_prompts_cache(page_size=100, timeout=120):
    return get_prompts(page_size=page_size, timeout=timeout)


def treat_data(response):
    cameras_aux = pd.read_csv("./data/database/cameras_aux.csv", dtype=str)

    cameras_aux = cameras_aux.rename(columns={"id_camera": "camera_id"})
    cameras = pd.DataFrame(response)
    cameras = cameras.rename(columns={"id": "camera_id"})
    cameras = cameras[cameras["identifications"].apply(lambda x: len(x) > 0)]
    if len(cameras) == 0:
        return None, None
    cameras = cameras.merge(cameras_aux, on="camera_id", how="left")
    # st.dataframe(cameras)

    cameras_attr = cameras[
        [
            "camera_id",
            "bairro",
            "subprefeitura",
            "name",
            # "rtsp_url",
            # "update_interval",
            "latitude",
            "longitude",
            "identifications",
            # "snapshot_url",
            # "id_h3",
            # "id_bolsao",
            # "bolsao_latitude",
            # "bolsao_longitude",
            # "bolsao_classe_atual",
            # "bacia",
            # "sub_bacia",
            # "geometry_bolsao_buffer_0.002",
        ]
    ]

    cameras_identifications_explode = explode_df(cameras_attr, "identifications")  # noqa

    cameras_identifications_explode = cameras_identifications_explode.rename(
        columns={"id": "object_id"}
    ).rename(columns={"camera_id": "id"})
    cameras_identifications_explode = cameras_identifications_explode.rename(
        columns={
            "snapshot.id": "snapshot_id",
            "snapshot.camera_id": "snapshot_camera_id",
            "snapshot.image_url": "snapshot_url",
            "snapshot.timestamp": "snapshot_timestamp",
        }
    )

    cameras_identifications_explode["timestamp"] = pd.to_datetime(
        cameras_identifications_explode["timestamp"], format="ISO8601"
    ).dt.tz_convert("America/Sao_Paulo")

    cameras_identifications_explode["snapshot_timestamp"] = pd.to_datetime(
        cameras_identifications_explode["snapshot_timestamp"], format="ISO8601"
    ).dt.tz_convert("America/Sao_Paulo")

    cameras_identifications_explode = cameras_identifications_explode.sort_values(  # noqa
        ["timestamp", "label"], ascending=False
    )

    # remove "image_description" from the objects
    cameras_identifications_explode = cameras_identifications_explode[
        cameras_identifications_explode["object"] != "image_description"
    ]

    # remove "null" from the labels
    cameras_identifications_explode = cameras_identifications_explode[
        cameras_identifications_explode["label"] != "null"
    ]

    # # create a column order to sort the labels
    cameras_identifications_explode = create_order_column(cameras_identifications_explode)
    # sort the table first by object then by the column order
    cameras_identifications_explode = cameras_identifications_explode.sort_values(
        ["object", "order"]
    )

    # translate the labels of the columns object and label to portuguese using the dictionary above
    cameras_identifications_explode["object"] = cameras_identifications_explode["object"].map(
        TRADUTOR
    )
    cameras_identifications_explode["label"] = cameras_identifications_explode["label"].map(
        TRADUTOR
    )

    # # print one random row of the dataframe in list format so I can see all the columns
    # print(cameras_identifications_explode.sample(1).values.tolist())

    # # print all columns of cameras_identifications_explode
    # print(cameras_identifications_explode.columns)

    return cameras_identifications_explode


def explode_df(dataframe, column_to_explode, prefix=None):
    df = dataframe.copy()
    exploded_df = df.explode(column_to_explode)
    new_df = pd.json_normalize(exploded_df[column_to_explode])

    if prefix:
        new_df = new_df.add_prefix(f"{prefix}_")

    df.drop(columns=column_to_explode, inplace=True)
    new_df.index = exploded_df.index
    result_df = df.join(new_df)

    return result_df


def get_objetcs_labels_df(objects, keep_null=False):
    objects_df = objects.rename(columns={"id": "object_id"})
    objects_df = objects_df[["name", "object_id", "labels"]]
    labels = explode_df(objects_df, "labels")
    if not keep_null:
        labels = labels[~labels["value"].isin(["null"])]
    labels = labels.rename(columns={"label_id": "label"})
    labels = labels.reset_index(drop=True)

    mask = (labels["value"] == "null") & (labels["name"] != "image_description")  # noqa
    labels = labels[~mask]
    return labels


def get_filted_cameras_objects(cameras_identifications_df, object_filter, label_filter):  # noqa
    # filter both dfs by object and label

    cameras_identifications_filter_df = cameras_identifications_df[
        (cameras_identifications_df["object"] == object_filter)
        & (cameras_identifications_df["label"].isin(label_filter))
    ]

    cameras_identifications_filter_df = cameras_identifications_filter_df.sort_values(  # noqa
        by=["timestamp", "label"], ascending=False
    )

    return cameras_identifications_filter_df


def get_icon_color(label: Union[bool, None], type=None):
    red = [
        "major",
        "totally_blocked",
        "impossible",
        "impossibe",
        "poor",
        "true",
        "flodding",
        "high",
        "totally",
    ]
    orange = [
        "minor",
        "partially_blocked",
        "difficult",
        "puddle",
        "medium",
        "moderate",
        "partially",
    ]

    green = [
        "normal",
        "free",
        "easy",
        "clean",
        "false",
        "low_indifferent",
        "low",
    ]
    if label in [TRADUTOR.get(label) for label in red]:  # noqa
        if type == "emoji":
            return "🔴"
        return "red"

    elif label in [TRADUTOR.get(label) for label in orange]:
        if type == "emoji":
            return "🟠"
        return "orange"
    elif label in [TRADUTOR.get(label) for label in green]:
        if type == "emoji":
            return "🟢"
        return "green"
    else:
        if type == "emoji":
            return "⚫"
        return "grey"


def create_map(chart_data, location=None):
    chart_data = chart_data.fillna("")
    # center map on the mean of the coordinates
    if location is not None:
        m = folium.Map(location=location, zoom_start=16)
    elif len(chart_data) > 0:
        m = folium.Map(
            location=[
                chart_data["latitude"].mean(),
                chart_data["longitude"].mean(),
            ],  # noqa
            zoom_start=11,
        )
    else:
        m = folium.Map(location=[-22.917690, -43.413861], zoom_start=11)

    for _, row in chart_data.iterrows():
        icon_color = get_icon_color(row["label"])
        htmlcode = f"""<div>
        <img src="{row["snapshot_url"]}" width="300" height="185">

        <br /><span>ID: {row["id"]}<br>Label: {row["label"]}</span>
        </div>
        """
        folium.Marker(
            location=[row["latitude"], row["longitude"]],
            # Adicionar id_camera ao tooltip
            tooltip=f"ID: {row['id']}<br>Label: {row['label']}",
            # Alterar a cor do ícone de acordo com o status
            popup=htmlcode,
            icon=folium.features.DivIcon(
                icon_size=(15, 15),
                icon_anchor=(7, 7),
                html=f'<div style="width: 15px; height: 15px; background-color: {icon_color}; border: 2px solid black; border-radius: 70%;"></div>',  # noqa
            ),
        ).add_to(m)
    return m


def display_camera_details(row, cameras_identifications_df):
    camera_id = row["id"]
    image_url = row["snapshot_url"]
    camera_name = row["name"]
    # snapshot_timestamp = row["snapshot_timestamp"].strftime("%d/%m/%Y %H:%M")  # noqa

    st.markdown(f"### 📷 Camera snapshot")  # noqa
    st.markdown(f"Endereço: {camera_name}")
    # st.markdown(f"Data Snapshot: {snapshot_timestamp}")

    # get cameras_attr url from selected row by id
    if image_url is None:
        st.markdown("Falha ao capturar o snapshot da câmera.")
    else:
        st.markdown(
            f"""<img src='{image_url}' style='max-width: 100%; max-height: 371px;'> """,
            unsafe_allow_html=True,
        )

    st.markdown("### 📃 Detalhes")
    camera_identifications = cameras_identifications_df[
        cameras_identifications_df["id"] == camera_id
    ]  # noqa

    # st.dataframe(camera_identifications)

    camera_identifications = camera_identifications.reset_index(drop=True)

    camera_identifications[""] = camera_identifications["label"].apply(
        lambda x: get_icon_color(x, type="emoji")
    )
    camera_identifications.index = camera_identifications[""]
    camera_identifications = camera_identifications[camera_identifications["timestamp"].notnull()]
    camera_identifications["timestamp"] = camera_identifications["timestamp"].apply(  # noqa
        lambda x: x.strftime("%d/%m/%Y %H:%M")
    )

    rename_columns = {
        "timestamp": "Data Identificação",
        "object": "Identificador",
        "label": "Classificação",
        "label_explanation": "Descrição",
    }
    camera_identifications = camera_identifications[list(rename_columns.keys())]  # noqa

    camera_identifications = camera_identifications.rename(columns=rename_columns)  # noqa

    # make a markdown with the first row of the dataframe and the first value of "Data Identificação"
    first_row = camera_identifications.iloc[0]
    markdown = f'<p><strong>Data Identificação:</strong> {first_row["Data Identificação"]}</p>'
    st.markdown(markdown, unsafe_allow_html=True)
    i = 0
    markdown = ""
    for _, row in camera_identifications.iterrows():
        critic_level = get_icon_color(row["Classificação"])
        # if critic_level = green, make classificacao have the color green and all capital letters
        if critic_level == "green":
            classificacao = f'<span style="color: green; text-transform: uppercase;">{row["Classificação"].upper()}</span>'
        # if critic_level = orange, make classificacao have the color orange and all capital letters
        elif critic_level == "orange":
            classificacao = f'<span style="color: orange; text-transform: uppercase;">{row["Classificação"].upper()}</span>'
        # if critic_level = red, make classificacao have the color red and all capital letters
        elif critic_level == "red":
            classificacao = f'<span style="color: red; text-transform: uppercase;">{row["Classificação"].upper()}</span>'
        else:
            classificacao = row["Classificação"].upper()
        # capitalize the identificador
        identificador = row["Identificador"].capitalize()
        # if i is even and not the last row
        if i % 2 == 0 and i != len(camera_identifications) - 1:
            markdown += f"""
            <div style="display: flex; margin-bottom: 10px;">
                <div style="flex: 1; border: 3px solid #ccc; border-radius: 5px; padding: 10px; margin-right: 10px;">
                    <p><strong>{identificador}</strong></p>
                    <p><strong>{classificacao}</strong></p>
                    <p><strong>Descrição:</strong> {row["Descrição"]}</p>
                </div>"""
        # if it is the last row, make it complete the row
        elif i == len(camera_identifications) - 1:
            markdown += f"""
                <div style="flex: 1; border: 3px solid #ccc; border-radius: 5px; padding: 10px; margin-right: 10px;">
                    <p><strong>{identificador}</strong></p>
                    <p><strong>{classificacao}</strong></p>
                    <p><strong>Descrição:</strong> {row["Descrição"]}</p>
                </div>
            </div>  <!-- Close the row here -->
            """
            st.markdown(markdown, unsafe_allow_html=True)
            markdown = ""
        else:
            markdown += f"""
                <div style="flex: 1; border: 3px solid #ccc; border-radius: 5px; padding: 10px; margin-right: 10px;">
                    <p><strong>{identificador}</strong></p>
                    <p><strong>{classificacao}</strong></p>
                    <p><strong>Descrição:</strong> {row["Descrição"]}</p>
                </div>
            </div>  <!-- Close the row here -->
            """
            st.markdown(markdown, unsafe_allow_html=True)
            markdown = ""
        i += 1


def display_agrid_table(table):
    gb = GridOptionsBuilder.from_dataframe(table, index=True)  # noqa

    gb.configure_column("index", header_name="", pinned="left")
    gb.configure_column("object", header_name="Identificador", wrapText=True)
    gb.configure_column("label", header_name="Classificação", wrapText=True)
    gb.configure_column("bairro", header_name="Bairro", wrapText=True)
    gb.configure_column("id", header_name="ID Camera", pinned="right")  # noqa
    gb.configure_column("timestamp", header_name="Data Identificação", wrapText=True)  # noqa
    # gb.configure_column(
    #     "snapshot_timestamp",
    #     header_name="Data Snapshot",
    #     hide=False,
    #     wrapText=True,  # noqa
    # )  # noqa
    gb.configure_column(
        "label_explanation",
        header_name="Descrição",
        cellStyle={"white-space": "normal"},
        autoHeight=True,
        wrapText=True,
        hide=True,
    )
    # gb.configure_column("old_snapshot", header_name="Predição Desatualizada")
    gb.configure_side_bar()
    gb.configure_selection("single", use_checkbox=False)
    gb.configure_grid_options(enableCellTextSelection=True)
    # gb.configure_pagination(paginationAutoPageSize=False, paginationPageSize=20)  # noqa
    grid_options = gb.build()
    grid_response = AgGrid(
        table,
        gridOptions=grid_options,
        columns_auto_size_mode=ColumnsAutoSizeMode.FIT_CONTENTS,
        update_mode=GridUpdateMode.MODEL_CHANGED | GridUpdateMode.COLUMN_RESIZED,  # noqa
        # fit_columns_on_grid_load=True,
        height=413,
        custom_css={
            "#gridToolBar": {
                "padding-bottom": "0px !important",
            }
        },
    )

    selected_row = grid_response["selected_rows"]

    return selected_row


def create_order_column(table):
    # dict with the order of the labels from the worst to the best
    order = {
        "road_blockade": [
            "totally",
            "partially",
            "free",
        ],
        "traffic": [
            "impossible",
            "difficult",
            "moderate",
            "easy",
        ],
        "rain": [
            "true",
            "false",
        ],
        "water_level": [
            "high",
            "medium",
            "low",
        ],
        "image_corrupted": [
            "true",
            "false",
        ],
    }

    # create a column order with the following rules:
    # 1. if the object is not in the order keys dict, return 99
    # 2. if the object is in the order keys, return the index of the label in the order list

    # knowing that the dataframe always have the columns object and label, we can use the following code
    table["order"] = table.apply(
        lambda row: order.get(row["object"], 99).index(row["label"]), axis=1
    )

    return table
