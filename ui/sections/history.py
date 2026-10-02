'''Review history table with undo.'''

import streamlit as st

from src.review_state import history_display, undo_last_review_state
from ui.components import build_column_config


def render_history() -> None:
    '''Show review log with reversible action.'''
    log_items = st.session_state.get('review_log', [])
    if not log_items:
        return
    st.markdown('<p class="body-text">Histórico de revisão</p>', unsafe_allow_html=True)
    display = history_display(list(log_items))
    st.dataframe(display, hide_index=True, column_config=build_column_config(display))
    if st.button('Desfazer última ação', key='undo_review', type='secondary'):
        undo_last_review_state(st.session_state)
        st.session_state['results_tab'] = 'potential'
        st.rerun()
