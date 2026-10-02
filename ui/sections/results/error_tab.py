'''Combined file error tables.'''

import pandas as pd
import streamlit as st

from src.report import _clean_error_frame
from ui.components import render_status_table


def format_error_display(frame: object) -> object:
    '''Translate Orientação to Como corrigir for display.'''
    if frame is None or len(frame) == 0:
        return pd.DataFrame(columns=['Linha', 'Motivo', 'Como corrigir'])
    return _clean_error_frame(frame)


def render_error_tab() -> None:
    '''Render combined file error tables.'''
    statement_errors = st.session_state.get('statement_errors')
    ledger_errors = st.session_state.get('ledger_errors')
    st.markdown('<p class="body-text">Erros do extrato</p>', unsafe_allow_html=True)
    render_status_table(format_error_display(statement_errors))
    st.markdown('<p class="body-text">Erros do interno</p>', unsafe_allow_html=True)
    render_status_table(format_error_display(ledger_errors))
