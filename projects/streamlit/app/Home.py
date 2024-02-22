# -*- coding: utf-8 -*-
# import folium # noqa

import streamlit as st
from streamlit_folium import st_folium  # noqa
from utils.utils import (
    create_map,
    display_agrid_table,
    display_camera_details,
    get_cameras,
    get_cameras_cache,
    get_filted_cameras_objects,
    get_icon_color,
    treat_data,
)

st.set_page_config(page_title="Vision AI - Rio", layout="wide", initial_sidebar_state="collapsed")
# st.image("./data/logo/logo.png", width=300)

DEFAULT_OBJECT = "nível da água"
st.markdown("## Identificações | Vision AI")


# Function to fetch and update data
def fetch_and_update_data(bypass_cash=False):
    page_size = 3000
    only_active = False
    use_mock_data = False
    update_mock_data = False

    if bypass_cash:
        return get_cameras(
            page_size=page_size,
            only_active=only_active,
            use_mock_data=use_mock_data,
            update_mock_data=update_mock_data,
        )
    return get_cameras_cache(
        page_size=page_size,
        only_active=only_active,
        use_mock_data=use_mock_data,
        update_mock_data=update_mock_data,
    )


cameras = fetch_and_update_data()
# Add a button for updating data
if st.button("Update Data"):
    cameras = fetch_and_update_data(bypass_cash=True)
    st.success("Data updated successfully!")


cameras_identifications = treat_data(cameras)
# st.dataframe(cameras_identifications)

if len(cameras_identifications) > 0:
    col1, col2 = st.columns(2)
    with col1:
        objects = cameras_identifications["object"].unique().tolist()
        objects.sort()
        # dropdown to filter by object
        object_filter = st.selectbox(
            "Filtrar por objeto",
            objects,
            index=objects.index(DEFAULT_OBJECT),
        )

    with col2:
        labels = (
            cameras_identifications[cameras_identifications["object"] == object_filter][  # noqa
                "label"
            ]
            .dropna()
            .unique()
            .tolist()
        )
        labels_default = labels.copy()

        # if object_filter == "road_blockade":
        #     labels_default.remove("normal")
        # dropdown to select label given selected object
        label_filter = st.multiselect(
            "Filtrar por label",
            labels,
            # if object_filter return minor and major, else return all labels
            default=labels_default,
        )

    cameras_identifications_filter = get_filted_cameras_objects(
        cameras_identifications_df=cameras_identifications,
        object_filter=object_filter,
        label_filter=label_filter,
    )
    # make two cols
    col1, col2 = st.columns(2)
    folium_map = create_map(cameras_identifications_filter)

    with col1:
        selected_cols = [
            "index",
            "object",
            "label",
            "bairro",
            "timestamp",
            "id",
        ]
        aggrid_table = cameras_identifications_filter.copy()
        aggrid_table["index"] = aggrid_table["label"].apply(
            lambda label: get_icon_color(label=label, type="emoji")
        )

        # sort the table first by object then by the column order
        aggrid_table = aggrid_table.sort_values(by=["object", "order"], ascending=[True, True])

        # capitalize the values of the columns object and label
        aggrid_table["object"] = aggrid_table["object"].str.capitalize()
        aggrid_table["label"] = aggrid_table["label"].str.capitalize()

        aggrid_table = aggrid_table[selected_cols]
        st.markdown("### 📈 Identificações")
        selected_row = display_agrid_table(aggrid_table)  # noqa

    with col2:
        if selected_row:
            camera_id = selected_row[0]["id"]
            row = cameras_identifications_filter[cameras_identifications_filter["id"] == camera_id]
            # get first row
            row = row.head(1).to_dict("records")[0]
            camera_location = [row["latitude"], row["longitude"]]
            folium_map = create_map(
                cameras_identifications_filter,
                location=camera_location,  # noqa
            )

            display_camera_details(
                row=row, cameras_identifications_df=cameras_identifications
            )  # noqa
        # if there is are ann object and label selected but no row is selected then select the first camera of the aggrid table
        elif object_filter and not selected_row and label_filter != []:
            camera_id = aggrid_table.head(1)["id"]
            # convert camera_id to string
            camera_id = camera_id.iloc[0]
            row = cameras_identifications_filter[cameras_identifications_filter["id"] == camera_id]
            # get first row
            row = row.head(1).to_dict("records")[0]
            camera_location = [row["latitude"], row["longitude"]]
            folium_map = create_map(
                cameras_identifications_filter,
                location=camera_location,  # noqa
            )

            display_camera_details(
                row=row, cameras_identifications_df=cameras_identifications
            )  # noqa
        else:
            st.markdown(
                """
                ### 📷 Câmera snapshot
                Selecione uma Câmera na tabela para visualizar mais detalhes.
                """
            )

    with col1:
        st.markdown("### 📍 Mapa")
        st_folium(folium_map, key="fig1", height=600, width="100%")

    # for camera_id in cameras_identifications_filter.index:
    #     row = cameras_filter.loc[camera_id]
    #     display_camera_details(
    #         row=row, cameras_identifications_df=cameras_identifications
    #     )
    #     time.sleep(2)
else:
    st.error("No cameras with identifications")
