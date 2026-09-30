'''Result tabs with kpis filters and review wiring.'''

import pandas as pd
import streamlit as st

from src.filters import (
    filter_by_period,
    filter_by_text,
    filter_by_value,
    normalize_period,
    pending_bounds,
    safe_ratio,
    value_bounds,
)
from src.review_state import active_frame, adjusted_counts, apply_manual_kpis
from ui.components import (
    build_match_display,
    build_pending_side,
    calc_kpis,
    format_pct,
    render_kpi_card,
    render_status_table,
)
from ui.sections.review import render_review_section
from ui.sections.upload import format_error_display


def render_empty_results() -> None:
    '''Render placeholder keeping right panel visible.'''
    st.markdown('<h2 class="display-md">Resultados</h2>', unsafe_allow_html=True)
    with st.container(border=True):
        st.markdown(
            '<p class="body-text">Nenhum resultado ainda.</p>',
            unsafe_allow_html=True,
        )
        st.caption('Envie os dois arquivos e clique em Conciliar.')


def render_kpi_section() -> None:
    '''Render five indicators plus exception bar.'''
    results = st.session_state.get('results')
    if results is None:
        render_empty_results()
        return
    statement_frame = st.session_state.get('statement_df')
    ledger_frame = st.session_state.get('ledger_df')
    statement_count = 0 if statement_frame is None else len(statement_frame)
    ledger_count = 0 if ledger_frame is None else len(ledger_frame)
    kpis = calc_kpis(results, statement_count, ledger_count)
    kpis = _apply_manual_kpis(kpis)
    st.markdown('<h2 class="display-md">Resultados</h2>', unsafe_allow_html=True)
    with st.container(horizontal=True):
        render_kpi_card('Total extrato', str(kpis['total_statement']))
        render_kpi_card('Total interno', str(kpis['total_ledger']))
        render_kpi_card('% Conciliado', format_pct(kpis['pct_auto']))
        render_kpi_card('% Para revisão', format_pct(kpis['pct_review']))
        render_kpi_card('% Pendente', format_pct(kpis['pct_pending']))
    st.progress(safe_ratio(kpis['pct_auto']))
    st.markdown(
        f'<p class="body-text">Taxa de exceção: {format_pct(kpis["exception_rate"])}</p>',
        unsafe_allow_html=True,
    )


def _apply_manual_kpis(kpis: dict) -> dict:
    '''Adjust percentages for confirmed rejected pairs.'''
    results = st.session_state.get('results')
    confirmed = st.session_state.get('manual_confirmed', set())
    rejected = st.session_state.get('manual_rejected', set())
    counts = adjusted_counts(results, confirmed, rejected)
    return apply_manual_kpis(kpis, counts)


def _filter_match_display(display: pd.DataFrame, prefix: str) -> pd.DataFrame:
    '''Apply search value period filters inside expander.'''
    box = st.expander(
        'Filtros', expanded=False, icon=':material/filter_list:', on_change='rerun',
        key=f'{prefix}_filters',
    )
    with box:
        query = st.text_input('Buscar descrição', key=f'{prefix}_search')
        filtered = filter_by_text(display, query)
        low, high = value_bounds(filtered)
        picked = st.slider('Valor', low, high, (low, high), key=f'{prefix}_value')
        filtered = filter_by_value(filtered, float(picked[0]), float(picked[1]))
        period = st.date_input('Período', value=None, key=f'{prefix}_period')
        start, end = normalize_period(period)
        return filter_by_period(filtered, start, end)


def render_match_tab(
    match_frame: pd.DataFrame, prefix: str, empty_label: str
) -> None:
    '''Render matched table with search value filters.'''
    statement_frame = st.session_state.get('statement_df')
    ledger_frame = st.session_state.get('ledger_df')
    confirmed = st.session_state.get('manual_confirmed', set())
    rejected = st.session_state.get('manual_rejected', set())
    results = st.session_state.get('results')
    active = active_frame(match_frame, prefix, confirmed, rejected, results)
    display = build_match_display(active, statement_frame, ledger_frame, confirmed)
    display = _filter_match_display(display, prefix)
    if len(display) == 0:
        st.markdown(f'<p class="body-text">{empty_label}</p>', unsafe_allow_html=True)
        return
    render_status_table(display)


def _filter_pending_sides(left_base: pd.DataFrame, right_base: pd.DataFrame) -> tuple:
    '''Apply pending search value period inside expander.'''
    box = st.expander(
        'Filtros', expanded=False, icon=':material/filter_list:', on_change='rerun',
        key='pending_filters',
    )
    with box:
        query = st.text_input('Buscar descrição', key='pending_search')
        left_filtered = filter_by_text(left_base, query)
        right_filtered = filter_by_text(right_base, query)
        low, high = pending_bounds(left_filtered, right_filtered)
        picked = st.slider('Valor', low, high, (low, high), key='pending_value')
        left_out = filter_by_value(left_filtered, float(picked[0]), float(picked[1]))
        right_out = filter_by_value(right_filtered, float(picked[0]), float(picked[1]))
        period = st.date_input('Período', value=None, key='pending_period')
        start, end = normalize_period(period)
        left_out = filter_by_period(left_out, start, end)
        right_out = filter_by_period(right_out, start, end)
        return (left_out, right_out)


def render_pending_tab() -> None:
    '''Render two unmatched tables with filters.'''
    results = st.session_state.get('results')
    pending = results.get('pending') if results else pd.DataFrame()
    statement_frame = st.session_state.get('statement_df')
    ledger_frame = st.session_state.get('ledger_df')
    left_base = build_pending_side(pending, statement_frame, 'statement')
    right_base = build_pending_side(pending, ledger_frame, 'ledger')
    left_display, right_display = _filter_pending_sides(left_base, right_base)
    st.markdown('<p class="body-text">Extrato sem par</p>', unsafe_allow_html=True)
    render_status_table(left_display)
    st.markdown('<p class="body-text">Interno sem par</p>', unsafe_allow_html=True)
    render_status_table(right_display)


def render_error_tab() -> None:
    '''Render combined file error tables.'''
    statement_errors = st.session_state.get('statement_errors')
    ledger_errors = st.session_state.get('ledger_errors')
    st.markdown('<p class="body-text">Erros do extrato</p>', unsafe_allow_html=True)
    render_status_table(format_error_display(statement_errors))
    st.markdown('<p class="body-text">Erros do interno</p>', unsafe_allow_html=True)
    render_status_table(format_error_display(ledger_errors))


def _result_tab_labels() -> list:
    '''Return six pt-BR tab labels with icons.'''
    return [
        ':material/check_circle: Conciliadas',
        ':material/rate_review: Para revisão',
        ':material/pending: Pendentes',
        ':material/warning: Divergentes',
        ':material/content_copy: Duplicadas',
        ':material/error: Erros',
    ]


def _show_auto_tab(tab: object, results: dict) -> None:
    '''Render conciliadas content when tab open.'''
    with tab:
        if tab.open is not False:
            render_match_tab(results.get('auto'), 'auto', 'Nenhuma conciliada ainda.')


def _show_potential_tab(tab: object, results: dict) -> None:
    '''Render revision content with review panel.'''
    with tab:
        if tab.open is not False:
            render_match_tab(results.get('potential'), 'potential', 'Nenhum par para revisão.')
            render_review_section()


def _show_simple_tab(tab: object, results: dict, frame_key: str, prefix: str, empty: str) -> None:
    '''Render single match tab when open.'''
    with tab:
        if tab.open is not False:
            render_match_tab(results.get(frame_key), prefix, empty)


def render_results_section() -> None:
    '''Render six tabs with pt-BR tables.'''
    results = st.session_state.get('results')
    if results is None:
        return
    tabs = st.tabs(_result_tab_labels(), key='results_tabs', on_change='rerun')
    _show_auto_tab(tabs[0], results)
    _show_potential_tab(tabs[1], results)
    with tabs[2]:
        if tabs[2].open is not False:
            render_pending_tab()
    _show_simple_tab(tabs[3], results, 'divergent', 'divergent', 'Nenhuma divergência.')
    _show_simple_tab(tabs[4], results, 'duplicate', 'duplicate', 'Nenhuma duplicada.')
    with tabs[5]:
        if tabs[5].open is not False:
            render_error_tab()
