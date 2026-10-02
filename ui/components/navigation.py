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


def _concepts_items() -> list:
    '''Return guide title body pairs in pt-BR.'''
    return [
        (
            '1. Captação de candidatos',
            'Cada lançamento do extrato é comparado com os internos e vira candidato quando '
            'o valor fica dentro da tolerância, o sinal é igual e a data cai na janela de dias. '
            'Tolerância maior significa rede maior: mais candidatos, nunca menos.',
        ),
        (
            '2. Classificação em 5 estados',
            'Conciliada: valor, data e descrição batem com um único candidato. Para revisão: há '
            'candidato próximo, mas algo impede o automático, como dois candidatos para a mesma '
            'linha. Pendente: sem candidato. Divergente: valor próximo com descrição muito '
            'diferente. Duplicada: linhas quase iguais dentro da mesma base.',
        ),
        (
            '3. Por que Conciliadas pode cair',
            'O automático exige candidato único. Ao aumentar a tolerância, uma linha pode ganhar '
            'um segundo candidato e ir para revisão por segurança: os pares não somem, mudam de '
            'estado. Acompanhe Conciliadas e Para revisão somadas, e espere Pendentes cair.',
        ),
    ]


def render_footer() -> None:
    '''Render footer box with embedded concepts guide.'''
    items = ''.join(
        f'<p><strong>{title}</strong><br>{body}</p>' for title, body in _concepts_items()
    )
    st.markdown(
        '<div class="footer"><details class="footer-guide">'
        '<summary>Como funciona a conciliação</summary>'
        f'{items}</details></div>',
        unsafe_allow_html=True,
    )
