'''Tolerance controls plus concile action.'''

from datetime import date, timedelta
from decimal import Decimal, InvalidOperation

import streamlit as st

from src.classifier import build_result_tables
from src.config import DATE_TOLERANCE_DAYS, FUZZY_THRESHOLD, VALUE_TOLERANCE
from src.logger import get_logger
from src.params import build_params

logger = get_logger(__name__)


def _example_pair(days: int) -> str:
    '''Build sample date pair spaced by day window.'''
    first = date(2026, 9, 11)
    second = first + timedelta(days=days)
    return f'{first:%d/%m} x {second:%d/%m}'


def _describe_days(days: int) -> str:
    '''Describe day tolerance window in plain words.'''
    if days <= 0:
        return 'Exige a mesma data nos dois lançamentos.'
    if days == 1:
        return f'1 dia cobre compensação D+1. Ex.: {_example_pair(1)} concilia.'
    return f'Cobre diferenças de até {days} dias (D+{days}). Ex.: {_example_pair(days)} concilia.'


def _describe_threshold(use_fuzzy: bool, threshold: int) -> str:
    '''Describe fuzzy threshold band in plain words.'''
    if not use_fuzzy:
        return 'Desligado: ignora o texto e usa só valor, sinal e data.'
    if threshold < 60:
        return 'Permissivo: concilia mais, pede mais revisão manual.'
    if threshold < 90:
        return 'Equilibra precisão e revisão manual. Ex.: Fornecedor X NF 1254 passa.'
    return 'Rígido: concilia menos, com menos falsos positivos.'


def _describe_value(raw: float | None) -> str:
    '''Describe value tolerance in plain words.'''
    if raw is None:
        return 'Exige valor exato.'
    if float(raw) <= 0:
        return 'Exige valor exato.'
    return f'Permite diferença de até {float(raw):.2f} com ponto decimal.'


def _render_days_input() -> int:
    '''Render day tolerance slider with live caption.'''
    days = st.slider('Tolerância de dias', 0, 30, DATE_TOLERANCE_DAYS)
    st.caption(_describe_days(int(days)))
    return int(days)


def _render_fuzzy_inputs() -> tuple[bool, int]:
    '''Render fuzzy toggle plus threshold with live caption.'''
    use_fuzzy = st.toggle('Usar similaridade de descrição', True)
    threshold = st.slider(
        'Similaridade mínima (%)', 0, 100, FUZZY_THRESHOLD, disabled=not bool(use_fuzzy),
    )
    st.caption(_describe_threshold(bool(use_fuzzy), int(threshold)))
    return (bool(use_fuzzy), int(threshold))


def _params_equal(first: dict, second: dict) -> bool:
    '''Compare engine params normalizing tolerance coercions.'''
    if set(first.keys()) != set(second.keys()):
        return False
    try:
        left = Decimal(str(first.get('value_tolerance')))
        right = Decimal(str(second.get('value_tolerance')))
        same_tolerance = left == right
    except (InvalidOperation, ValueError, TypeError, AttributeError):
        return False
    return (
        first.get('date_tolerance_days') == second.get('date_tolerance_days')
        and first.get('fuzzy_threshold') == second.get('fuzzy_threshold')
        and first.get('use_fuzzy') == second.get('use_fuzzy')
        and same_tolerance
    )


def _render_stale_warning() -> None:
    '''Warn when params changed after last conciliation.'''
    if st.session_state.get('results') is None:
        return
    frozen = st.session_state.get('results_params')
    current = st.session_state.get('params')
    if not isinstance(current, dict):
        return
    if not isinstance(frozen, dict):
        st.caption('Parâmetros alterados após a conciliação. Clique em Conciliar novamente.')
        return
    if not _params_equal(dict(frozen), dict(current)):
        st.caption('Parâmetros alterados após a conciliação. Clique em Conciliar novamente.')


def _render_value_input() -> float:
    '''Render value tolerance input with live caption.'''
    raw = st.number_input(
        'Tolerância de valor (R$)', min_value=0.00, max_value=None, value=float(VALUE_TOLERANCE),
        step=0.01,
    )
    if raw is None:
        raw = 0.0
    st.caption(_describe_value(float(raw)))
    return float(raw)


def _store_params_from_inputs(inputs: tuple[int, int, float, bool]) -> None:
    '''Validate inputs storing engine params in session.'''
    date_tolerance_days, fuzzy_threshold, raw_tolerance, use_fuzzy = inputs
    try:
        st.session_state['params'] = build_params(
            date_tolerance_days=date_tolerance_days,
            fuzzy_threshold=fuzzy_threshold,
            value_tolerance=Decimal(str(raw_tolerance)),
            use_fuzzy=bool(use_fuzzy),
        )
    except ValueError as exc:
        st.error(str(exc))


def render_params_section() -> None:
    '''Render tolerance card storing engine params.'''
    st.markdown('<h2 class="display-md">2. Parâmetros</h2>', unsafe_allow_html=True)
    with st.container(border=True):
        date_tolerance_days = _render_days_input()
        use_fuzzy, fuzzy_threshold = _render_fuzzy_inputs()
        raw_tolerance = _render_value_input()
        _store_params_from_inputs(
            (date_tolerance_days, fuzzy_threshold, raw_tolerance, use_fuzzy)
        )
        render_concile_button()
        _render_stale_warning()


def render_concile_button() -> None:
    '''Execute matching storing five result tables.'''
    pressed = st.button(
        'Conciliar', key='concile_action', type='primary', width='stretch',
        icon=':material/compare_arrows:',
    )
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
    with st.spinner('Conciliando lançamentos...'):
        try:
            params = st.session_state.get('params', build_params())
            st.session_state['results'] = build_result_tables(statement_frame, ledger_frame, params)
            st.session_state['results_params'] = dict(params)
            st.session_state['manual_confirmed'] = set()
            st.session_state['manual_rejected'] = set()
            st.session_state['results_tab'] = 'auto'
            st.success('Conciliação concluída. Veja os resultados abaixo.')
        except ValueError as exc:
            st.error(str(exc))
        except (RuntimeError, KeyError) as exc:
            logger.warning(f'Matching failed with {exc}')
            st.error('Não foi possível conciliar. Verifique os arquivos e parâmetros.')
