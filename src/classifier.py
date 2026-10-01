'''Classifier with five states ambiguity and duplicates.'''

from src.classification.ambiguity import (
    _build_match_id,
    _count_links,
    _group_by,
    _pick_best,
    _sort_key,
    resolve_ambiguity,
)
from src.classification.duplicates import (
    _MATCH_COLUMNS,
    _build_duplicate_table,
    _duplicate_row,
    _empty_frame,
    detect_duplicates,
)
from src.classification.pending import (
    _build_amount_index,
    _build_pending_table,
    _collect_all_pending_rows,
    _collect_simple_entries,
    _is_signal_blocked,
    _pending_row,
    _pending_rows,
    _pending_side,
    _resolve_pending_limits,
)
from src.classification.rules import (
    _as_decimal,
    _decide_cents,
    _decide_exact,
    _decide_value_fuzzy,
    _extract_fields,
    _params_snapshot,
    classify_match,
)
from src.classification.tables import (
    _assemble_tables,
    _classify_all,
    _classify_single,
    _frame_from_rows,
    _include_dups,
    _match_row,
    build_result_tables,
)
from src.labels import STATUS_LABEL_PT as _shared_status

STATUS_LABEL_PT = dict(_shared_status)

__all__ = [
    '_MATCH_COLUMNS',
    '_as_decimal',
    '_assemble_tables',
    '_build_amount_index',
    '_build_duplicate_table',
    '_build_match_id',
    '_build_pending_table',
    '_classify_all',
    '_classify_single',
    '_collect_all_pending_rows',
    '_collect_simple_entries',
    '_count_links',
    '_decide_cents',
    '_decide_exact',
    '_decide_value_fuzzy',
    '_duplicate_row',
    '_empty_frame',
    '_extract_fields',
    '_frame_from_rows',
    '_group_by',
    '_include_dups',
    '_is_signal_blocked',
    '_match_row',
    '_params_snapshot',
    '_pending_row',
    '_pending_rows',
    '_pending_side',
    '_pick_best',
    '_resolve_pending_limits',
    '_sort_key',
    'STATUS_LABEL_PT',
    'build_result_tables',
    'classify_match',
    'detect_duplicates',
    'resolve_ambiguity',
]
