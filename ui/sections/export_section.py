'''Left aligned download block for reports.'''

import streamlit as st

from src.params import params_equal


def _resolve_export_params(session: object) -> tuple:
    '''Return frozen params plus stale flag from session mapping.'''
    try:
        current = session.get('params')
        frozen = session.get('results_params')
    except (AttributeError, TypeError):
        return None, False
    if not isinstance(frozen, dict):
        params = current if isinstance(current, dict) else None
        return params, True
    if not isinstance(current, dict):
        return dict(frozen), True
    stale = not params_equal(dict(frozen), dict(current))
    return dict(frozen), stale


def _manual_decision_count(session: object) -> int:
    '''Count confirmed plus rejected pairs in session mapping.'''
    try:
        confirmed = session.get('manual_confirmed', set())
        rejected = session.get('manual_rejected', set())
    except (AttributeError, TypeError):
        return 0
    if not isinstance(confirmed, (set, list, tuple, frozenset)):
        confirmed = set()
    if not isinstance(rejected, (set, list, tuple, frozenset)):
        rejected = set()
    try:
        return len(confirmed) + len(rejected)
    except (TypeError, AttributeError):
        return 0


def _provenance_line(session: object) -> str:
    '''Build manual count caption.'''
    total = _manual_decision_count(session)
    if total <= 0:
        return ''
    if total == 1:
        return 'Inclui 1 decisão manual'
    return f'Inclui {total} decisões manuais'


def _has_export_bytes(payload: object) -> bool:
    '''Check download payload is non empty bytes.'''
    return isinstance(payload, bytes) and len(payload) > 0


def _render_excel_download(excel_bytes: bytes) -> None:
    '''Render excel button or failure notice.'''
    if not _has_export_bytes(excel_bytes):
        st.error('Relatório Excel indisponível. Concilie novamente.')
        return
    st.download_button(
        'Baixar relatório em Excel',
        data=excel_bytes,
        file_name='relatorio_conciliacao.xlsx',
        mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        key='download_excel',
        width='stretch',
        type='primary',
        icon=':material/table_chart:',
    )
    st.caption('8 abas: resumo, resultados, erros e log de regras.')


def _render_csv_download(csv_bytes: bytes) -> None:
    '''Render csv button or failure notice.'''
    if not _has_export_bytes(csv_bytes):
        st.error('CSV de exceções indisponível. Concilie novamente.')
        return
    st.download_button(
        'Baixar só exceções (CSV)',
        data=csv_bytes,
        file_name='relatorio_excecoes.csv',
        mime='text/csv',
        key='download_csv',
        width='stretch',
        type='secondary',
        icon=':material/filter_list:',
    )
    st.caption('Para tratar pendências.')


def render_download_buttons(excel_bytes: bytes, csv_bytes: bytes) -> None:
    '''Render two equal width download actions.'''
    left, right = st.columns(2, gap='medium')
    with left:
        _render_excel_download(excel_bytes)
    with right:
        _render_csv_download(csv_bytes)


def _render_stale_caption() -> None:
    '''Warn when params changed after last conciliation.'''
    _, stale = _resolve_export_params(st.session_state)
    if stale:
        st.caption(
            'Parâmetros alterados após a conciliação. '
            'O arquivo usa os parâmetros conciliados.'
        )


def render_export_section(results: object, excel_bytes: bytes, csv_bytes: bytes) -> None:
    '''Render download block with content and manual count.'''
    if results is None:
        return
    st.markdown('<h2 class="display-md">Exportar relatórios</h2>', unsafe_allow_html=True)
    with st.container(border=True):
        st.markdown(
            '<p class="body-text">Excel com 8 abas (resumo, resultados por estado, '
            'erros e log de regras) e CSV só com exceções.</p>',
            unsafe_allow_html=True,
        )
        line = _provenance_line(st.session_state)
        if line:
            st.caption(line)
        _render_stale_caption()
        render_download_buttons(excel_bytes, csv_bytes)
    st.caption('Dúvidas sobre os estados? Veja Como funciona a conciliação abaixo.')
