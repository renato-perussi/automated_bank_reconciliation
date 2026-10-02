'''Result tabs facade preserving legacy imports.'''

from ui.sections.results.duplicate_tab import render_duplicate_tab
from ui.sections.results.error_tab import format_error_display, render_error_tab
from ui.sections.results.kpis import (
    _apply_manual_kpis,
    _kpi_items,
    _next_action_line,
    _open_work_line,
    _render_kpi_cards,
    render_empty_results,
    render_kpi_section,
)
from ui.sections.results.match_tab import _filter_match_display, render_match_tab
from ui.sections.results.pending_tab import _filter_pending_sides, render_pending_tab
from ui.sections.results.tabs import (
    _RESULT_TABS,
    _active_len,
    _default_tab_label,
    _error_total,
    _frame_len,
    _result_tab_labels,
    _show_auto_tab,
    _show_potential_tab,
    _show_simple_tab,
    _tab_label,
    _tab_total,
    render_results_section,
)

__all__ = [
    '_RESULT_TABS',
    '_active_len',
    '_apply_manual_kpis',
    '_default_tab_label',
    '_error_total',
    '_filter_match_display',
    '_filter_pending_sides',
    '_frame_len',
    '_kpi_items',
    '_next_action_line',
    '_open_work_line',
    '_render_kpi_cards',
    '_result_tab_labels',
    '_show_auto_tab',
    '_show_potential_tab',
    '_show_simple_tab',
    '_tab_label',
    '_tab_total',
    'format_error_display',
    'render_duplicate_tab',
    'render_empty_results',
    'render_error_tab',
    'render_kpi_section',
    'render_match_tab',
    'render_pending_tab',
    'render_results_section',
]
