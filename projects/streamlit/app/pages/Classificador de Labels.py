# -*- coding: utf-8 -*-
import json

import pandas as pd
import streamlit as st
from utils.utils import explode_df, get_objects_cache, get_objetcs_labels_df

st.set_page_config(
    page_title="Classificador de Labels",
    layout="wide",
    initial_sidebar_state="collapsed",
)
# st.image("./data/logo/logo.png", width=300)

st.markdown("# Classificador de labels | Vision AI")

objects = pd.DataFrame(get_objects_cache())

labels = get_objetcs_labels_df(objects)
# labels.index = labels["name"]
# labels = labels.drop(columns=["name"])


# https://docs.google.com/document/d/1PRCjbIJw4_g3-p4gLjYoN0qTaenephyZyOsiOfVGWzM/edit


def get_translation(label):
    markdown_translation = [
        {
            "object": "image_corrupted",
            "title": "A imagem está corrompida?",
            "condition": "Se a resposta for 'Sim', pule para a próxima imagem.",  # noqa
            "explanation": "Confira se os detalhes na imagem estão claros e definidos. Uma imagem considerada nítida permite a identificação dos objetos e do cenário.",  # noqa
            "labels": {
                "true": "Sim",
                "false": "Não",
            },
        },
        {
            "object": "rain",
            "title": "Há indício de chuva?",
            "condition": "Se a resposta for 'Não', associe o rótulo ‘Baixa ou Indiferente’ à opção 3 e pule para 4.",  # noqa
            "explanation": " Inspeção visual para presença de água na pista, que pode variar desde uma leve umidade até condições de alagamento evidente.",  # noqa
            "labels": {
                "true": "Sim",
                "false": "Não",
            },
        },
        {
            "object": "water_level",
            "title": "Qual o nível de acúmulo de água?",
            "condition": "Se a resposta for 'Não', pule para a próxima imagem.",  # noqa
            "explanation": "Estime o volume de água presente na pista, categorizando-o como um muito baixa (menos que ¼ da roda de um veículo de passeio), bolsão (entre ¼ e  ½ da roda), ou alagamento (mais que ½ da roda).",  # noqa
            "labels": {
                "low": "Baixa ou Indiferente",
                "medium": "Bolsão d'água",
                "high": "Alagamento",
            },
        },
        {
            "object": "road_blockade",
            "title": "Há algum bloqueio na via?",
            "condition": "",
            "explanation": "Avalie se há algum obstáculo na via que impeça a circulação de veículos. O obstáculo pode ser um acúmulo de água, árvore caída, carro enguiçado, entre outros.",  # noqa
            "labels": {
                "free": "Sem obstáculos",
                "partially": "Via parcialmente bloqueada",
                "totally": "Via bloqueada",
            },
        },
    ]

    for translation in markdown_translation:
        if translation["object"] == label:
            return translation


snapshots_identifications = [
    {
        "object": "image_corrupted",
        "label": "none",
    },
    {
        "object": "rain",
        "label": "none",
    },
    {
        "object": "water_level",
        "label": "none",
    },
    {
        "object": "road_blockade",
        "label": "none",
    },
]

mock_snapshots = pd.read_csv("./data/temp/mock_image_classification.csv")
mock_snapshots_list = mock_snapshots["image_url"].tolist()
snapshots = [
    {
        "snapshot_url": snapshot_url,
        "snapshot_identification": list(snapshots_identifications),
    }
    for snapshot_url in mock_snapshots_list
]

snapshots_objects = explode_df(pd.DataFrame(data=snapshots), "snapshot_identification")  # noqa

objects_number = {
    object_name: i + 1
    for i, object_name in enumerate(snapshots_objects["object"].unique().tolist())  # noqa
}
snapshots_objects["question_number"] = snapshots_objects["object"].map(objects_number)  # noqa


def put_selected_label(label, snapshots_options):
    snapshots_to_put = snapshots_options.to_dict()
    snapshots_to_put["label"] = label
    # # TODO: make a put for selected object/label
    if (snapshots_to_put.get("object") == "image_corrupted") and (label == "true"):  # noqa
        print("HEREEE")
        st.session_state.row_index += 3

    print(json.dumps(snapshots_to_put, indent=4), "\n")


customized_button = st.markdown(
    """
    <style >
    div.stButton > button:first-child {
        height: 100% !important;
        width: 100% !important;
        font-size: 15px !important;
        padding-top: 10px !important;
        padding-bottom: 10px !important;
    }
    </style>""",
    unsafe_allow_html=True,
)


def buttom(
    label,
    label_translated,
    row,
):
    if st.button(
        label_translated,
        on_click=put_selected_label,
        args=(
            label,
            row,
        ),
    ):  # noqa
        pass


# Create a state variable to keep track of the current image index
if "row_index" not in st.session_state:
    st.session_state.row_index = 0


# Check if there are more images to review
if st.session_state.row_index >= len(snapshots_objects):
    st.write("You have reviewed all images.")
    if st.button("Reset"):
        st.markdown("TODO: Reset the state variables and start over.")

else:
    # Get the current image from the DataFrame
    row = snapshots_objects.iloc[st.session_state.row_index]  # noqa
    # Extract relevant information
    name = row["object"]
    translate_dict = get_translation(name)
    snapshot_url = row["snapshot_url"]
    question_number = row["question_number"]
    labels_options = labels[labels["name"] == name]

    choices = labels_options["value"].tolist()
    choices.sort()

    if "true" in choices:
        choices = ["true", "false"]

    # st.write"
    col1, col2 = st.columns([1, 1.5])
    with col2:
        st.image(snapshot_url)
    with col1:
        st.markdown(
            f"### {question_number}.  {translate_dict.get('title')}",
        )
        st.markdown(
            f"**Explicação:** {translate_dict.get('explanation')}",
        )
    # place labels in a grid of 2 columns
    for i, label in enumerate(choices):
        label_translated = translate_dict.get("labels").get(label)
        with col1:
            buttom(
                label=label,
                label_translated=label_translated,
                row=row,
            )
        # else:
        #     with col4:
        #         buttom(
        #             label=label,
        #             label_translated=label_translated,
        #             row=row,
        #         )

    st.session_state.row_index += 1  # noqa
