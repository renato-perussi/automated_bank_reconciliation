'''Review cards and option labels.'''

import pandas as pd
import streamlit as st

from ui.components.base import _display_amount, _display_date, _display_text


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
    rule = _display_text(detail.get('Regra'))
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
        st.badge(rule, icon=':material/rule:', color='gray')


def review_option_label(row: pd.Series) -> str:
    '''Build rich select label from raw match row.'''
    pair = str(row.get('match_id', '—'))
    days = str(row.get('day_diff', '—'))
    score = str(row.get('description_score', '—'))
    rule = str(row.get('rule_id', '—'))
    return f'{pair} • {days} dia(s) • similaridade {score} • {rule}'
