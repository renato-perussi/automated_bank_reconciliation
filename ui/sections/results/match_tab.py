'''Matched pair tab with filters.'''

import pandas as pd
import streamlit as st

from src.review_state import active_frame
from ui.components import build_match_display, render_status_table
from ui.sections.result_filters import filter_match_display

_filter_match_display = filter_match_display


def render_match_tab(match_frame: pd.DataFrame, prefix: str, empty_label: str) -> None:
    '''Render matched table with search value filters.'''
    statement_frame = st.session_state.get('statement_df')
    ledger_frame = st.session_state.get('ledger_df')
    confirmed = st.session_state.get('manual_confirmed', set())
    rejected = st.session_state.get('manual_rejected', set())
    results = st.session_state.get('results')
    active = active_frame(match_frame, prefix, confirmed, rejected, results)
    base_total = 0 if active is None else len(active)
    display = build_match_display(active, statement_frame, ledger_frame, confirmed)
    display = _filter_match_display(display, prefix)
    if len(display) == 0:
        st.markdown(f'<p class="body-text">{empty_label}</p>', unsafe_allow_html=True)
        if base_total > 0:
            st.caption('Nenhum item passa pelos filtros. Ajuste a busca ou limpe os filtros.')
        return
    render_status_table(display)
