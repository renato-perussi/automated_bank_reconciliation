'''Pending unmatched tables with filters.'''

import pandas as pd
import streamlit as st

from ui.components import build_pending_side, render_status_table
from ui.sections.result_filters import filter_pending_sides

_filter_pending_sides = filter_pending_sides


def render_pending_tab() -> None:
    '''Render two unmatched tables with filters.'''
    results = st.session_state.get('results')
    pending = results.get('pending') if results else pd.DataFrame()
    statement_frame = st.session_state.get('statement_df')
    ledger_frame = st.session_state.get('ledger_df')
    left_base = build_pending_side(pending, statement_frame, 'statement')
    right_base = build_pending_side(pending, ledger_frame, 'ledger')
    left_display, right_display = _filter_pending_sides(left_base, right_base)
    st.markdown(
        f'<p class="body-text">Extrato sem par ({len(left_display)})</p>',
        unsafe_allow_html=True,
    )
    render_status_table(left_display)
    st.markdown(
        f'<p class="body-text">Interno sem par ({len(right_display)})</p>',
        unsafe_allow_html=True,
    )
    render_status_table(right_display)
