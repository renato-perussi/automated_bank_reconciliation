'''Tab labels counts and section wiring.'''

import streamlit as st

from src.review_state import active_frame
from ui.sections.results.match_tab import render_match_tab
from ui.sections.review import render_review_section


def _tab_label(icon: str, name: str, total: int) -> str:
    '''Build tab label hiding zero counts.'''
    if total > 0:
        return f'{icon} {name} ({total})'
    return f'{icon} {name}'


def _frame_len(frame: object) -> int:
    '''Return row count tolerating missing frames.'''
    return 0 if frame is None else len(frame)


def _active_len(results: dict, frame_key: str, prefix: str) -> int:
    '''Count visible rows honoring manual review sets.'''
    confirmed = st.session_state.get('manual_confirmed', set())
    rejected = st.session_state.get('manual_rejected', set())
    active = active_frame(results.get(frame_key), prefix, confirmed, rejected, results)
    return _frame_len(active)


def _error_total() -> int:
    '''Count combined file error rows.'''
    return _frame_len(st.session_state.get('statement_errors')) + _frame_len(
        st.session_state.get('ledger_errors')
    )


def _tab_total(results: dict, key: str) -> int:
    '''Count visible rows for tab key.'''
    if key == 'pending':
        return _frame_len(results.get('pending'))
    if key == 'errors':
        return _error_total()
    return _active_len(results, key, key)


_RESULT_TABS = [
    ('auto', ':material/check_circle:', 'Conciliadas'),
    ('potential', ':material/rate_review:', 'Para revisão'),
    ('pending', ':material/pending:', 'Pendentes'),
    ('divergent', ':material/warning:', 'Divergentes'),
    ('duplicate', ':material/content_copy:', 'Duplicadas'),
    ('errors', ':material/error:', 'Erros'),
]


def _result_tab_labels(results: dict) -> list:
    '''Return six pt-BR tab labels with icons and live counts.'''
    return [
        _tab_label(icon, name, _tab_total(results, key)) for key, icon, name in _RESULT_TABS
    ]


def _default_tab_label(labels: list) -> str | None:
    '''Resolve stored tab target to current label.'''
    keys = [key for key, _, _ in _RESULT_TABS]
    wanted = st.session_state.get('results_tab')
    if wanted in keys:
        return labels[keys.index(wanted)]
    return None


def _show_auto_tab(tab: object, results: dict) -> None:
    '''Render conciliadas content inside tab.'''
    with tab:
        render_match_tab(results.get('auto'), 'auto', 'Nenhuma conciliada ainda.')


def _show_potential_tab(tab: object, results: dict) -> None:
    '''Render reference table first with review panel below.'''
    with tab:
        potential = results.get('potential')
        render_match_tab(potential, 'potential', 'Nenhum par para revisão.')
        if potential is None or len(potential) == 0:
            return
        render_review_section()


def _show_simple_tab(tab: object, results: dict, frame_key: str, prefix: str, empty: str) -> None:
    '''Render single match tab content.'''
    with tab:
        render_match_tab(results.get(frame_key), prefix, empty)


def render_results_section() -> None:
    '''Render six client side tabs with pt-BR tables.'''
    from ui.sections.results.duplicate_tab import render_duplicate_tab
    from ui.sections.results.error_tab import render_error_tab
    from ui.sections.results.pending_tab import render_pending_tab
    results = st.session_state.get('results')
    if results is None:
        return
    labels = _result_tab_labels(results)
    tabs = st.tabs(labels, key='results_tabs', default=_default_tab_label(labels))
    _show_auto_tab(tabs[0], results)
    _show_potential_tab(tabs[1], results)
    with tabs[2]:
        render_pending_tab()
    _show_simple_tab(tabs[3], results, 'divergent', 'divergent', 'Nenhuma divergência.')
    with tabs[4]:
        render_duplicate_tab()
    with tabs[5]:
        render_error_tab()
