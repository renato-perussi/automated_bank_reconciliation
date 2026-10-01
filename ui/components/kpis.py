'''Kpi grid and metric wrappers.'''

import streamlit as st

from src.report import calc_kpis as _shared_kpis
from ui.components.base import format_brl, format_pct

__all__ = ['format_brl', 'format_pct']


def render_kpi_grid(items: list) -> None:
    '''Render wrapping metrics row for narrow screens.'''
    if not items:
        return
    with st.container(horizontal=True):
        for item in items:
            label, value = item[0], item[1]
            hint = item[2] if len(item) > 2 else None
            st.metric(str(label), str(value), border=True, help=hint)


def render_kpi_card(label: str, value: str) -> None:
    '''Render single native indicator with border.'''
    st.metric(str(label), str(value), border=True)


def calc_kpis(results: dict, statement_count: int, ledger_count: int) -> dict:
    '''Calculate totals and percentages from result tables.'''
    return _shared_kpis(results, statement_count, ledger_count)
