'''Duplicate single side list with filters.'''

import pandas as pd
import streamlit as st

from ui.components import build_duplicate_display, render_status_table
from ui.sections.results.match_tab import _filter_match_display


def render_duplicate_tab() -> None:
    '''Render single side duplicate list with filters.'''
    results = st.session_state.get('results')
    dup = results.get('duplicate') if results else pd.DataFrame()
    statement_frame = st.session_state.get('statement_df')
    ledger_frame = st.session_state.get('ledger_df')
    display = build_duplicate_display(dup, statement_frame, ledger_frame)
    display = _filter_match_display(display, 'duplicate')
    base_total = 0 if dup is None else len(dup)
    if len(display) == 0:
        st.markdown('<p class="body-text">Nenhuma duplicada.</p>', unsafe_allow_html=True)
        if base_total > 0:
            st.caption('Nenhum item passa pelos filtros. Ajuste a busca ou limpe os filtros.')
        return
    render_status_table(display)
