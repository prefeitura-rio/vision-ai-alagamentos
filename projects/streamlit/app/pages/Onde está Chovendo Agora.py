# -*- coding: utf-8 -*-
import streamlit as st

st.set_page_config(
    page_title="Onde está Chovendo Agora",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# embed a webpage that covers all screen
st.write(
    '<iframe src="https://www.dados.rio/chuvas/onde-esta-chovendo-agora" style="position:fixed; top:0; left:0; bottom:0; right:0; width:100%; height:100%; border:none; margin:0; padding:0; overflow:hidden;"></iframe>',  # noqa
    unsafe_allow_html=True,
)

# Position the text at the specified location with custom styling
st.write(
    """
    <a href="https://www.dados.rio/chuvas/onde-esta-chovendo-agora" target="_blank" style="text-decoration: none;">
        <div style="position: fixed; bottom: 60px; right: 20px; border: 2px solid white; border-radius: 15px; padding: 10px;">
            <span style="color: white; font-weight: bold;">Abrir em nova aba</span>
        </div>
    </a>
    """,
    unsafe_allow_html=True,
)
