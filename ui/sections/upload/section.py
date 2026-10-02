'''Single and double upload card assembly.'''

import pandas as pd
import streamlit as st

from ui.sections.upload.file_io import fetch_raw_table
from ui.sections.upload.mapping_ui import choose_mapping, finalize_source
from ui.sections.upload.preview_ui import _render_source_status, show_preview_errors


def render_single_upload(
    uploader_label: str, source: str, frame_key: str, error_key: str, prefix: str
) -> tuple:
    '''Render one uploader with mapping and status.'''
    uploaded = st.file_uploader(uploader_label, type=['csv', 'xlsx'], key=f'{prefix}_up')
    if uploaded is None:
        st.session_state[frame_key] = None
        st.session_state[error_key] = pd.DataFrame()
        return None, None, None, None
    raw_frame = fetch_raw_table(uploaded)
    if raw_frame is None:
        st.session_state[frame_key] = None
        st.session_state[error_key] = pd.DataFrame()
        return None, None, None, None
    mapping = choose_mapping(raw_frame, prefix)
    valid, errors = finalize_source(raw_frame, mapping, source)
    st.session_state[frame_key] = valid
    st.session_state[error_key] = errors
    _render_source_status(valid, errors)
    return raw_frame, valid, errors, mapping


def render_upload_section() -> None:
    '''Render title plus two upload cards side by side.'''
    st.markdown('<h2 class="display-md">1. Upload dos arquivos</h2>', unsafe_allow_html=True)
    st.markdown(
        '<p class="body-text">Selecione os dois arquivos. Nada sai deste computador.</p>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<p class="upload-note">CSV ou Excel, até 20 MB por arquivo</p>',
        unsafe_allow_html=True,
    )
    left_upload, right_upload = st.columns(2, gap='medium')
    with left_upload:
        with st.container(border=True):
            left_raw, _, left_errors, left_mapping = render_single_upload(
                'Extrato bancário', 'statement', 'statement_df', 'statement_errors', 'statement'
            )
    with right_upload:
        with st.container(border=True):
            right_raw, _, right_errors, right_mapping = render_single_upload(
                'Lançamentos internos', 'ledger', 'ledger_df', 'ledger_errors', 'ledger'
            )
    if left_raw is not None:
        show_preview_errors(
            left_raw, left_errors, 'statement', 'Prévia do extrato', left_mapping
        )
    if right_raw is not None:
        show_preview_errors(
            right_raw, right_errors, 'ledger', 'Prévia dos lançamentos internos', right_mapping
        )
