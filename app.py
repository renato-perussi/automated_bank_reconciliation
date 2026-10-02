'''Streamlit interface for bank reconciliation flow.'''

import pandas as pd
import streamlit as st

from src.export_service import build_export_bytes
from src.matcher import build_params
from ui.components import load_styles, render_footer, render_header, render_subnav
from ui.sections.export_section import render_export_section
from ui.sections.params_section import render_params_section
from ui.sections.results import render_kpi_section, render_results_section
from ui.sections.upload import render_upload_section


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
    if 'results_tab' not in st.session_state:
        st.session_state['results_tab'] = 'auto'


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
    frozen = st.session_state.get('results_params')
    if isinstance(frozen, dict):
        params = dict(frozen)
    else:
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
