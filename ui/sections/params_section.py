'''Tolerance controls plus concile action.'''

from decimal import Decimal

import streamlit as st

from src.classifier import build_result_tables
from src.config import DATE_TOLERANCE_DAYS, FUZZY_THRESHOLD, VALUE_TOLERANCE
from src.logger import get_logger
from src.matcher import build_params

logger = get_logger(__name__)


def render_params_section() -> None:
    '''Render tolerance controls storing engine params.'''
    st.markdown('<h2 class="display-md">Parâmetros</h2>', unsafe_allow_html=True)
    date_tolerance_days = st.slider('Tolerância de dias', 0, 30, DATE_TOLERANCE_DAYS)
    st.caption('2 dias cobre compensação D+1.')
    fuzzy_threshold = st.slider('Similaridade mínima (%)', 0, 100, FUZZY_THRESHOLD)
    use_fuzzy = st.toggle('Usar similaridade de descrição', True)
    st.caption('85 equilibra precisão e revisão manual.')
    raw_tolerance = st.number_input(
        'Tolerância de valor (R$)', 0.00, 10.00, float(VALUE_TOLERANCE), step=0.01
    )
    st.caption('0,00 exige valor exato. Ex.: 0,05 permite centavos.')
    try:
        st.session_state['params'] = build_params(
            date_tolerance_days=date_tolerance_days,
            fuzzy_threshold=fuzzy_threshold,
            value_tolerance=Decimal(str(raw_tolerance)),
            use_fuzzy=bool(use_fuzzy),
        )
    except ValueError as exc:
        st.error(str(exc))


def render_concile_button() -> None:
    '''Execute matching storing five result tables.'''
    pressed = st.button('Conciliar', key='concile_action', type='primary', width='stretch')
    if not pressed:
        return
    statement_frame = st.session_state.get('statement_df')
    ledger_frame = st.session_state.get('ledger_df')
    if statement_frame is None or ledger_frame is None:
        st.error('Envie os dois arquivos para conciliar.')
        return
    if len(statement_frame) == 0 or len(ledger_frame) == 0:
        st.error('Arquivos sem linhas válidas. Corrija os erros e tente novamente.')
        return
    try:
        params = st.session_state.get('params', build_params())
        st.session_state['results'] = build_result_tables(statement_frame, ledger_frame, params)
        st.session_state['manual_confirmed'] = set()
        st.session_state['manual_rejected'] = set()
        st.success('Conciliação concluída. Veja os resultados abaixo.')
    except ValueError as exc:
        st.error(str(exc))
    except (RuntimeError, KeyError) as exc:
        logger.warning(f'Matching failed with {exc}')
        st.error('Não foi possível conciliar. Verifique os arquivos e parâmetros.')
