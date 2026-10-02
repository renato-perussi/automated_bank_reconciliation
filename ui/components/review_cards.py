'''Review cards and option labels.'''

import pandas as pd
import streamlit as st

from src.labels import reason_short as _shared_reason_short
from ui.components.base import _display_amount, _display_date, _display_text, side_triple


def render_review_cards(detail: pd.Series) -> None:
    '''Render extrato interno cards plus neutral badges.'''
    date_left = _display_date(detail.get('Data extrato'))
    desc_left = _display_text(detail.get('Descrição extrato'))
    amount_left = _display_amount(detail.get('Valor extrato'))
    date_right = _display_date(detail.get('Data interno'))
    desc_right = _display_text(detail.get('Descrição interno'))
    amount_right = _display_amount(detail.get('Valor interno'))
    days = _display_text(detail.get('Diferença dias'))
    value = _display_text(detail.get('Diferença valor'))
    score = _display_text(detail.get('Similaridade'))
    motive = _shared_reason_short(_display_text(detail.get('Motivo')))
    left_col, right_col = st.columns(2)
    with left_col:
        with st.container(border=True):
            st.markdown('**Extrato**')
            st.markdown(f'{date_left} • {amount_left}')
            st.caption(desc_left)
    with right_col:
        with st.container(border=True):
            st.markdown('**Interno**')
            st.markdown(f'{date_right} • {amount_right}')
            st.caption(desc_right)
    with st.container(horizontal=True):
        st.badge(f'{days} dia(s)', icon=':material/schedule:', color='gray')
        st.badge(value, icon=':material/payments:', color='gray')
        st.badge(f'Similaridade {score}', icon=':material/analytics:', color='gray')
        if motive != '—':
            st.badge(motive, icon=':material/info:', color='gray')


def _short_description(text: object, limit: int = 45) -> str:
    '''Truncate long description keeping single line label.'''
    clean = _display_text(text)
    if len(clean) <= limit:
        return clean
    return clean[:limit].rstrip() + '…'


def review_option_label(row: pd.Series, statement_frame: object = None) -> str:
    '''Build user friendly select label from extrato triple.'''
    motive = _shared_reason_short(_display_text(row.get('reason')))
    if statement_frame is None:
        return motive
    date_val, desc_val, amount_val = side_triple(statement_frame, row.get('statement_idx'))
    parts = [
        _display_date(date_val),
        _short_description(desc_val),
        _display_amount(amount_val),
    ]
    if motive and motive != '—':
        parts.append(motive)
    return ' • '.join(parts)
