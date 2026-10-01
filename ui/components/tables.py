'''Result table config and rendering.'''

import pandas as pd
import streamlit as st


def build_column_config(frame: pd.DataFrame) -> dict:
    '''Build typed config with BRL text dates and pinned id.'''
    config: dict = {}
    if frame is None or len(frame) == 0:
        return config
    for field in ['Valor', 'Valor extrato', 'Valor interno', 'Diferença valor']:
        if field in list(frame.columns):
            config[field] = st.column_config.TextColumn()
    for field in ['Data', 'Data extrato', 'Data interno']:
        if field in list(frame.columns):
            config[field] = st.column_config.TextColumn()
    if 'Data/Hora' in list(frame.columns):
        config['Data/Hora'] = st.column_config.TextColumn()
    if 'Par ID' in list(frame.columns):
        config['Par ID'] = st.column_config.TextColumn(pinned=True)
    return config


def render_status_table(frame: pd.DataFrame) -> None:
    '''Render result table with empty pt-BR fallback.'''
    if frame is None or len(frame) == 0:
        st.markdown(
            '<p class="body-text">Nenhum registro encontrado.</p>', unsafe_allow_html=True
        )
        return
    st.dataframe(frame, hide_index=True, column_config=build_column_config(frame))
