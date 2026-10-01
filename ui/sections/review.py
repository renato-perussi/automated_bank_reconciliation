'''Side by side manual review inside revision tab.'''

import pandas as pd
import streamlit as st

from src.labels import reason_label as _shared_reason_label
from src.review_state import confirm_pair_state, filtered_review_rows, reject_pair_state
from ui.components import build_match_display, render_review_cards, review_option_label
from ui.sections.history import render_history


def _reason_label(raw: object) -> str:
    '''Translate internal motive code to pt-BR text.'''
    return _shared_reason_label(raw)


def _build_lookup(available: object) -> dict:
    '''Index rich labels by match id.'''
    lookup: dict = {}
    for _, item in available.iterrows():
        pair = str(item.get('match_id'))
        lookup[pair] = review_option_label(item)
    return lookup


def _pick_review_row(available: object) -> tuple:
    '''Select review pair returning chosen row.'''
    options = available['match_id'].astype(str).tolist()
    lookup = _build_lookup(available)
    chosen = st.selectbox(
        'Selecione o par (extrato → interno)', options, key='review_pick',
        format_func=lambda item: lookup.get(str(item), str(item)),
    )
    row = available[available['match_id'].astype(str) == str(chosen)].iloc[0]
    return (chosen, row)


def _render_feedback() -> None:
    '''Show one-shot full width action message.'''
    message = st.session_state.get('feedback')
    if not message:
        return
    st.success(message)
    st.session_state['feedback'] = None


def _render_review_actions(chosen: str) -> None:
    '''Render confirm reject buttons plus feedback history.'''
    confirm_col, reject_col = st.columns(2)
    with confirm_col:
        confirm = st.button(
            'Confirmar', key='confirm_pair', type='primary', width='stretch',
            icon=':material/check:',
        )
        if confirm:
            confirm_pair_state(st.session_state, str(chosen))
            st.rerun()
    with reject_col:
        reject = st.button(
            'Rejeitar', key='reject_pair', type='secondary', width='stretch',
            icon=':material/close:',
        )
        if reject:
            reject_pair_state(st.session_state, str(chosen))
            st.rerun()
    _render_feedback()
    render_history()


def render_pair_detail(row: pd.Series) -> None:
    '''Show side by side cards badges and motive.'''
    statement_frame = st.session_state.get('statement_df')
    ledger_frame = st.session_state.get('ledger_df')
    display = build_match_display(pd.DataFrame([row]), statement_frame, ledger_frame, set())
    detail = display.iloc[0] if len(display) > 0 else None
    if detail is None:
        return
    render_review_cards(detail)
    st.markdown(
        '<p class="body-text motivo-line"><span class="label-strong">Motivo:</span> '
        f'{_reason_label(detail.get("Motivo"))}</p>',
        unsafe_allow_html=True,
    )


def _render_empty_review() -> None:
    '''Show empty hint plus history when present.'''
    log_items = st.session_state.get('review_log', [])
    if not log_items:
        st.caption('Nenhuma ação manual ainda.')
        return
    render_history()


def render_review_section() -> None:
    '''Render side by side review inside revision tab.'''
    results = st.session_state.get('results')
    if results is None:
        return
    potential = results.get('potential')
    if potential is None or len(potential) == 0:
        _render_empty_review()
        return
    confirmed = st.session_state.get('manual_confirmed', set())
    rejected = st.session_state.get('manual_rejected', set())
    available = filtered_review_rows(potential, confirmed, rejected)
    if len(available) == 0:
        _render_empty_review()
        return
    st.markdown('<div class="review-divider"></div>', unsafe_allow_html=True)
    st.markdown(
        '<p class="body-text"><span class="label-strong">Resultado lado a lado</span>'
        ' — extrato x interno</p>',
        unsafe_allow_html=True,
    )
    chosen, row = _pick_review_row(available)
    render_pair_detail(row)
    _render_review_actions(chosen)
