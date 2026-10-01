'''Centered download buttons for reports.'''

import streamlit as st

from src.review_state import adjusted_counts


def _export_counts(results: object) -> str:
    '''Summarize adjusted tables for download hint.'''
    try:
        confirmed = st.session_state.get('manual_confirmed', set())
        rejected = st.session_state.get('manual_rejected', set())
        auto_len, pot_len, pend_len, _, _, _, _ = adjusted_counts(results, confirmed, rejected)
        return f'{auto_len} conciliadas • {pot_len} para revisão • {pend_len} pendentes'
    except (AttributeError, TypeError, KeyError, ValueError):
        return 'Relatório com regra aplicada e versão do motor'


def render_download_buttons(excel_bytes: bytes, csv_bytes: bytes) -> None:
    '''Render two equal width download actions.'''
    left, right = st.columns(2, gap='medium')
    with left:
        st.download_button(
            'Baixar Excel',
            data=excel_bytes,
            file_name='relatorio_conciliacao.xlsx',
            mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            key='download_excel',
            width='stretch',
            type='primary',
            icon=':material/download:',
        )
    with right:
        st.download_button(
            'Baixar CSV de exceções',
            data=csv_bytes,
            file_name='relatorio_excecoes.csv',
            mime='text/csv',
            key='download_csv',
            width='stretch',
            type='secondary',
            icon=':material/download:',
        )


def render_export_section(results: object, excel_bytes: bytes, csv_bytes: bytes) -> None:
    '''Render bordered download block for reports.'''
    if results is None:
        return
    st.markdown(
        '<h2 class="display-md export-center">Exportar relatórios</h2>', unsafe_allow_html=True
    )
    with st.container(border=True):
        st.markdown(
            '<p class="body-text">Baixe o relatório completo e o CSV só '
            'com exceções.</p>',
            unsafe_allow_html=True,
        )
        st.caption(_export_counts(results))
        render_download_buttons(excel_bytes, csv_bytes)
