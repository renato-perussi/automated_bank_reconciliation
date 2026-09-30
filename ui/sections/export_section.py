'''Centered download buttons for reports.'''

import streamlit as st


def render_download_buttons(excel_bytes: bytes, csv_bytes: bytes) -> None:
    '''Render two side by side download actions.'''
    left, right = st.columns(2)
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
            type='primary',
            icon=':material/download:',
        )


def render_export_section(results: object, excel_bytes: bytes, csv_bytes: bytes) -> None:
    '''Render centered download buttons for reports.'''
    if results is None:
        return
    st.divider()
    st.markdown(
        '<h2 class="display-md export-center">Exportar relatórios</h2>', unsafe_allow_html=True
    )
    st.markdown(
        '<p class="body-text export-center">Baixe o relatório completo e o CSV de exceções.</p>',
        unsafe_allow_html=True,
    )
    _, outer_center, _ = st.columns([1, 2, 1])
    with outer_center:
        render_download_buttons(excel_bytes, csv_bytes)
