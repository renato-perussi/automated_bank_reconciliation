'''Kpi cards and action line for results.'''

import streamlit as st

from src.review_state import adjusted_counts, apply_manual_kpis, filtered_review_rows
from ui.components import calc_kpis, format_pct, render_kpi_grid


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


def _next_action_line(review_count: int, pending_count: int) -> str:
    '''Build one line telling user where work remains.'''
    if review_count <= 0 and pending_count <= 0:
        return 'Tudo resolvido — nada aguarda ação.'
    parts = []
    if review_count == 1:
        parts.append('1 par aguarda revisão')
    elif review_count > 1:
        parts.append(f'{review_count} pares aguardam revisão')
    if pending_count == 1:
        parts.append('1 item sem par')
    elif pending_count > 1:
        parts.append(f'{pending_count} itens sem par')
    return ' • '.join(parts) + '.'


def _render_kpi_cards(kpis: dict, action_line: str) -> None:
    '''Render kpi grid plus next action and exception hero.'''
    st.markdown('<h2 class="display-md">3. Resultados</h2>', unsafe_allow_html=True)
    render_kpi_grid(_kpi_items(kpis))
    st.caption('Totais por base • % sobre total unificado.')
    st.markdown(f'<p class="body-text">{action_line}</p>', unsafe_allow_html=True)
    st.markdown(
        f'<p class="exception-hero">Taxa de exceção: {format_pct(kpis["exception_rate"])}</p>',
        unsafe_allow_html=True,
    )
    st.caption('Exceção = tudo que não conciliou sozinho.')


def _apply_manual_kpis(kpis: dict) -> dict:
    '''Adjust percentages for confirmed rejected pairs.'''
    results = st.session_state.get('results')
    confirmed = st.session_state.get('manual_confirmed', set())
    rejected = st.session_state.get('manual_rejected', set())
    counts = adjusted_counts(results, confirmed, rejected)
    return apply_manual_kpis(kpis, counts)


def _open_work_line(results: dict) -> str:
    '''Count review queue and unmatched rows for action line.'''
    confirmed = st.session_state.get('manual_confirmed', set())
    rejected = st.session_state.get('manual_rejected', set())
    potential = results.get('potential')
    if potential is None or len(potential) == 0:
        review_open = 0
    else:
        review_open = len(filtered_review_rows(potential, confirmed, rejected))
    pending_frame = results.get('pending')
    pending_open = 0 if pending_frame is None else len(pending_frame)
    return _next_action_line(review_open, pending_open)


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
    _render_kpi_cards(kpis, _open_work_line(results))
