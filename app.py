'''Streamlit interface for bank reconciliation flow.'''

import pandas as pd
import streamlit as st

from src.export_service import build_export_bytes
from src.filters import filter_by_period as _filter_period
from src.filters import filter_by_text as _filter_text
from src.filters import filter_by_value as _filter_value
from src.labels import reason_label as _shared_reason_label
from src.matcher import build_params
from src.report import _clean_error_frame
from src.review_state import adjusted_counts as _counts
from src.review_state import apply_manual_kpis as _kpis
from src.review_state import confirm_pair_state, reject_pair_state, undo_last_review_state
from src.review_state import history_display as _history_frame
from src.review_state import history_label as _history_name
from src.review_state import history_moment as _history_time
from ui.components import (
    load_styles,
    render_footer,
    render_header,
    render_subnav,
)
from ui.sections.export_section import render_export_section
from ui.sections.params_section import render_params_section
from ui.sections.results import render_kpi_section, render_results_section
from ui.sections.upload import fetch_raw_table as _fetch_table
from ui.sections.upload import render_upload_section
from ui.sections.upload import save_temp_file as _save_temp


def init_state() -> None:
    '''Ensure session keys for flow state.'''
    if 'statement_df' not in st.session_state:
        st.session_state['statement_df'] = None
    if 'ledger_df' not in st.session_state:
        st.session_state['ledger_df'] = None
    if 'params' not in st.session_state:
        st.session_state['params'] = build_params()
    if 'results' not in st.session_state:
        st.session_state['results'] = None
    if 'results_params' not in st.session_state:
        st.session_state['results_params'] = None
    if 'review_log' not in st.session_state:
        st.session_state['review_log'] = []
    if 'manual_confirmed' not in st.session_state:
        st.session_state['manual_confirmed'] = set()
    if 'manual_rejected' not in st.session_state:
        st.session_state['manual_rejected'] = set()
    if 'statement_errors' not in st.session_state:
        st.session_state['statement_errors'] = pd.DataFrame()
    if 'ledger_errors' not in st.session_state:
        st.session_state['ledger_errors'] = pd.DataFrame()
    if 'feedback' not in st.session_state:
        st.session_state['feedback'] = None


def save_temp_file(uploaded_file: object) -> object:
    '''Persist upload preserving suffix for loader.'''
    return _save_temp(uploaded_file)


def fetch_raw_table(uploaded_file: object) -> object:
    '''Load raw table from upload with pt-BR feedback.'''
    return _fetch_table(uploaded_file)


def filter_by_text(frame: object, query: str) -> object:
    '''Filter display rows by description substring.'''
    return _filter_text(frame, query)


def filter_by_value(frame: object, low: float, high: float) -> object:
    '''Filter display rows by numeric value window.'''
    return _filter_value(frame, low, high)


def filter_by_period(frame: object, start: object, end: object) -> object:
    '''Filter display rows by date window.'''
    return _filter_period(frame, start, end)


def format_error_display(frame: object) -> object:
    '''Translate Orientação to Como corrigir for display.'''
    if frame is None or len(frame) == 0:
        return pd.DataFrame(columns=['Linha', 'Motivo', 'Como corrigir'])
    return _clean_error_frame(frame)


def _reason_label(raw: object) -> str:
    '''Translate internal motive code to pt-BR text.'''
    return _shared_reason_label(raw)


def _history_label(action: object) -> str:
    '''Translate review action to pt-BR.'''
    return _history_name(action)


def _history_moment(raw: object) -> str:
    '''Format iso timestamp to pt-BR display.'''
    return _history_time(raw)


def _history_display(log_items: list) -> object:
    '''Build pt-BR history frame for display.'''
    return _history_frame(log_items)


def _adjusted_counts() -> tuple:
    '''Compute effective auto potential after manual review.'''
    results = st.session_state.get('results')
    confirmed = st.session_state.get('manual_confirmed', set())
    rejected = st.session_state.get('manual_rejected', set())
    return _counts(results, confirmed, rejected)


def _apply_manual_kpis(kpis: dict) -> dict:
    '''Adjust percentages for confirmed rejected pairs.'''
    return _kpis(kpis, _adjusted_counts())


def confirm_pair(pair_id: str) -> None:
    '''Mark pair manual moving to conciliadas.'''
    confirm_pair_state(st.session_state, str(pair_id))
    st.rerun()


def reject_pair(pair_id: str) -> None:
    '''Reject pair returning to pendente pool.'''
    reject_pair_state(st.session_state, str(pair_id))
    st.rerun()


def undo_last_review() -> None:
    '''Revert last manual decision in session.'''
    undo_last_review_state(st.session_state)
    st.rerun()


@st.cache_data(ttl=600, max_entries=5)
def _cached_export_payloads(
    results: dict,
    params: dict,
    statement_frame: object,
    ledger_frame: object,
    statement_errors: object,
    ledger_errors: object,
    review_log: object,
) -> tuple:
    '''Build cached excel csv bytes from hashable inputs.'''
    return build_export_bytes(
        results, params, statement_frame, ledger_frame,
        statement_errors, ledger_errors, review_log,
    )


def build_export_payloads() -> tuple:
    '''Build excel csv bytes in memory without files.'''
    results = st.session_state.get('results')
    params = st.session_state.get('params', build_params())
    statement_frame = st.session_state.get('statement_df')
    ledger_frame = st.session_state.get('ledger_df')
    statement_errors = st.session_state.get('statement_errors')
    ledger_errors = st.session_state.get('ledger_errors')
    review_log = st.session_state.get('review_log', [])
    return _cached_export_payloads(
        results, params, statement_frame, ledger_frame, statement_errors, ledger_errors,
        review_log,
    )


def main() -> None:
    '''Run vertical funnel with full width results.'''
    st.set_page_config(
        page_title='Conciliação Bancária', layout='centered', page_icon=':material/account_balance:'
    )
    init_state()
    load_styles()
    render_header()
    render_subnav()
    render_upload_section()
    render_params_section()
    render_kpi_section()
    render_results_section()
    results = st.session_state.get('results')
    excel_bytes, csv_bytes = build_export_payloads() if results is not None else (b'', b'')
    render_export_section(results, excel_bytes, csv_bytes)
    render_footer()


if __name__ == '__main__':
    main()
