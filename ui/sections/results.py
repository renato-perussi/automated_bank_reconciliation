'''Result tabs with kpis filters and review wiring.'''

import pandas as pd
import streamlit as st

from src.filters import safe_ratio
from src.review_state import active_frame, adjusted_counts, apply_manual_kpis
from ui.components import (
    build_match_display,
    build_pending_side,
    calc_kpis,
    format_pct,
    render_kpi_grid,
    render_status_table,
)
from ui.sections.result_filters import filter_match_display, filter_pending_sides
from ui.sections.review import render_review_section
from ui.sections.upload import format_error_display


def render_empty_results() -> None:
    '''Render placeholder keeping right panel visible.'''
    st.markdown('<h2 class="display-md">3. Resultados</h2>', unsafe_allow_html=True)
    with st.container(border=True):
        st.markdown(
            '<p class="body-text">Nenhuma conciliação ainda — envie os 2 arquivos '
            'e clique em Conciliar.</p>',
            unsafe_allow_html=True,
        )
        st.caption('Você verá aqui Conciliadas, Para revisão, Pendentes, Divergentes e Erros.')


def _kpi_items(kpis: dict) -> list:
    '''Build five pt-BR indicator pairs.'''
    return [
        ('Total extrato', str(kpis['total_statement'])),
        ('Total interno', str(kpis['total_ledger'])),
        ('% Conciliado', format_pct(kpis['pct_auto'])),
        ('% Revisão', format_pct(kpis['pct_review'])),
        ('% Pendente', format_pct(kpis['pct_pending'])),
    ]


def _render_kpi_cards(kpis: dict) -> None:
    '''Render kpi grid plus exception hero.'''
    st.markdown('<h2 class="display-md">3. Resultados</h2>', unsafe_allow_html=True)
    render_kpi_grid(_kpi_items(kpis))
    st.caption(
        'Totais por base • % sobre total unificado • Pendente inclui divergente e duplicada.'
    )
    st.progress(safe_ratio(kpis['pct_auto']))
    st.markdown(
        f'<p class="exception-hero">Taxa de exceção: {format_pct(kpis["exception_rate"])}</p>',
        unsafe_allow_html=True,
    )
    st.caption('Exceção = 100% menos conciliado automático. Meta: menos de 30% em revisão.')


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
    _render_kpi_cards(kpis)


def _apply_manual_kpis(kpis: dict) -> dict:
    '''Adjust percentages for confirmed rejected pairs.'''
    results = st.session_state.get('results')
    confirmed = st.session_state.get('manual_confirmed', set())
    rejected = st.session_state.get('manual_rejected', set())
    counts = adjusted_counts(results, confirmed, rejected)
    return apply_manual_kpis(kpis, counts)


def _filter_match_display(display: pd.DataFrame, prefix: str) -> pd.DataFrame:
    '''Apply search value period filters inside expander.'''
    return filter_match_display(display, prefix)


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
    base_total = 0 if active is None else len(active)
    display = build_match_display(active, statement_frame, ledger_frame, confirmed)
    display = _filter_match_display(display, prefix)
    if len(display) == 0:
        st.markdown(f'<p class="body-text">{empty_label}</p>', unsafe_allow_html=True)
        if base_total > 0:
            st.caption('Nenhum item passa pelos filtros. Ajuste a busca ou limpe os filtros.')
        return
    render_status_table(display)


def _filter_pending_sides(left_base: pd.DataFrame, right_base: pd.DataFrame) -> tuple:
    '''Apply pending search value period inside expander.'''
    return filter_pending_sides(left_base, right_base)


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
    '''Render conciliadas content inside tab.'''
    with tab:
        render_match_tab(results.get('auto'), 'auto', 'Nenhuma conciliada ainda.')


def _show_potential_tab(tab: object, results: dict) -> None:
    '''Render revision content with review panel.'''
    with tab:
        render_match_tab(results.get('potential'), 'potential', 'Nenhum par para revisão.')
        render_review_section()


def _show_simple_tab(tab: object, results: dict, frame_key: str, prefix: str, empty: str) -> None:
    '''Render single match tab content.'''
    with tab:
        render_match_tab(results.get(frame_key), prefix, empty)


def render_results_section() -> None:
    '''Render six client side tabs with pt-BR tables.'''
    results = st.session_state.get('results')
    if results is None:
        return
    tabs = st.tabs(_result_tab_labels(), key='results_tabs')
    _show_auto_tab(tabs[0], results)
    _show_potential_tab(tabs[1], results)
    with tabs[2]:
        render_pending_tab()
    _show_simple_tab(tabs[3], results, 'divergent', 'divergent', 'Nenhuma divergência.')
    _show_simple_tab(tabs[4], results, 'duplicate', 'duplicate', 'Nenhuma duplicada.')
    with tabs[5]:
        render_error_tab()
