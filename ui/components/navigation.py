'''Navigation header subnav footer.'''

from pathlib import Path

import streamlit as st

from src.logger import get_logger

logger = get_logger(__name__)


def load_styles() -> None:
    '''Inject shared stylesheet into streamlit page.'''
    style_path = Path(__file__).resolve().parent.parent / 'styles.css'
    try:
        css_text = style_path.read_text(encoding='utf-8')
    except OSError as exc:
        logger.warning(f'Style load failed with {exc}')
        return
    st.markdown(f'<style>{css_text}</style>', unsafe_allow_html=True)


def render_header() -> None:
    '''Render hero title and subtitle.'''
    st.markdown(
        '<header class="hero-section">'
        '<h1 class="display-lg">Conciliação Bancária</h1>'
        '<p class="body-text hero-subtitle">Compare o extrato com os lançamentos '
        'internos em poucos passos.</p></header>',
        unsafe_allow_html=True,
    )


def current_step() -> int:
    '''Derive funnel position from session tables.'''
    if st.session_state.get('results') is not None:
        return 3
    has_statement = st.session_state.get('statement_df') is not None
    has_ledger = st.session_state.get('ledger_df') is not None
    if has_statement or has_ledger:
        return 2
    return 1


def _step_class(position: int, active: int) -> str:
    '''Map step position to done active todo.'''
    if position < active:
        return 'step-done'
    if position == active:
        return 'step-active'
    return 'step-todo'


def _step_marker(position: int, state: str) -> str:
    '''Return check for done steps else position number.'''
    if state == 'step-done':
        return '✓'
    return str(position)


def _step_item(position: int, label: str, active: int) -> str:
    '''Build single stepper list item with pill number.'''
    state = _step_class(position, active)
    marker = _step_marker(position, state)
    current = ' aria-current="step"' if position == active else ''
    return (
        f'<li class="step-item {state}"{current}>'
        f'<span class="step-num" aria-hidden="true">{marker}</span>'
        f'<span class="step-label">{label}</span></li>'
    )


def render_subnav() -> None:
    '''Render frosted stepper with funnel state.'''
    active = current_step()
    first = _step_item(1, 'Upload', active)
    second = _step_item(2, 'Parâmetros', active)
    third = _step_item(3, 'Resultados', active)
    st.markdown(
        '<nav class="sub-nav-frosted" aria-label="Progresso">'
        f'<ol class="step-list">{first}{second}{third}</ol></nav>',
        unsafe_allow_html=True,
    )


def _concept_upload_items() -> list:
    '''Return upload guide bullets in pt-BR.'''
    return [
        'Suba o extrato bancário e os lançamentos internos em CSV ou '
        'Excel (até 20 MB cada).',
        'Só três colunas importam — data, descrição e valor — e valem '
        'apelidos como date, histórico e amount.',
        'Se o app não reconhecer alguma coluna, o painel Mapear colunas '
        'abre sozinho.',
        'Colunas extras não atrapalham, mas não entram na conciliação.',
        'Confira as prévias, ajuste os parâmetros só se precisar e clique '
        'em Conciliar.',
    ]


def _concept_result_items() -> list:
    '''Return result guide bullets in pt-BR.'''
    return [
        'Conciliadas não pedem ação.',
        'Para revisão pede seu olho: escolha o par, compare lado a lado e '
        'clique em Confirmar ou Rejeitar (dá para desfazer).',
        'Pendentes não acharam par; Divergentes têm valor parecido com '
        'descrição bem diferente; Duplicadas se repetem dentro da mesma base.',
    ]


def _concept_export_items() -> list:
    '''Return export guide bullets in pt-BR.'''
    return [
        'O Excel traz 8 abas com tudo, incluindo suas decisões manuais e '
        'a versão do motor.',
        'O CSV traz só as exceções para tratar.',
        'Se mudar algum parâmetro depois de conciliar, clique em Conciliar '
        'de novo antes de baixar.',
    ]


def _concepts_items() -> list:
    '''Return guide title plus bullet pairs in pt-BR.'''
    return [
        ('1. Envie os arquivos e clique em Conciliar', _concept_upload_items()),
        ('2. Leia o resultado por aba', _concept_result_items()),
        ('3. Baixe os relatórios', _concept_export_items()),
    ]


def _guide_block(title: str, bullets: list) -> str:
    '''Build titled bullet list for footer guide.'''
    items = ''.join(f'<li>{bullet}</li>' for bullet in bullets)
    return f'<p><strong>{title}</strong></p><ul>{items}</ul>'


def render_footer() -> None:
    '''Render footer box with embedded concepts guide.'''
    items = ''.join(
        _guide_block(title, bullets) for title, bullets in _concepts_items()
    )
    st.markdown(
        '<div class="footer"><details class="footer-guide">'
        '<summary>Como funciona a conciliação</summary>'
        f'{items}</details></div>',
        unsafe_allow_html=True,
    )
