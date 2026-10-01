'''Matched and single side detail rows.'''

from src.guards import is_missing
from src.reporting.formatting import _as_number
from src.reporting.headers import _manual_label, _reason_label, _status_label
from src.reporting.lookups import _extract_side


def _display_pair_id(pair: object) -> str:
    '''Return blank for missing pandas pair id.'''
    if pair is None:
        return ''
    if is_missing(pair):
        return ''
    return pair


def _display_rule_id(rule: object) -> str:
    '''Return blank for missing pandas rule id.'''
    if rule is None:
        return ''
    if is_missing(rule):
        return ''
    return rule


def _display_reason_motive(reason: object) -> str:
    '''Return blank or pt-BR motive for pandas reason.'''
    if reason is None:
        return ''
    if is_missing(reason):
        return ''
    return _reason_label(reason)


def _display_metric_number(metric: object) -> object:
    '''Return blank for missing pandas metric number.'''
    if metric is None:
        return ''
    if is_missing(metric):
        return ''
    return metric


def _matched_rows(
    match_frame: object, statement_df: object, ledger_frame: object, status: str, manual: dict
) -> list:
    '''Expand matched pairs into two pt-BR rows.'''
    rows: list = []
    if match_frame is None or len(match_frame) == 0:
        return rows
    for _, item in match_frame.iterrows():
        pair = item.get('match_id')
        manual_entry = manual.get(str(pair), {})
        label = _manual_label(manual_entry.get('review_action', ''))
        rows.append(_matched_side(item, statement_df, True, status, label))
        rows.append(_matched_side(item, ledger_frame, False, status, label))
    return rows


def _build_detail_dict(
    origin: str,
    side: dict,
    status: str,
    pair: object,
    day_diff: object,
    value_diff: object,
    score: object,
    rule: object,
    reason: object,
    label: str,
) -> dict:
    '''Build pt-BR detail dict from side and audit fields.'''
    return {
        'Origem': origin, 'Data original': side['orig_date'],
        'Data normalizada': side['norm_date'],
        'Descrição original': side['orig_desc'],
        'Valor original': side['orig_amount'],
        'Valor normalizado': side['norm_value'],
        'Sinal': side['sign'],
        'Status': status,
        'Par ID': _display_pair_id(pair),
        'Diferença dias': _display_metric_number(day_diff),
        'Diferença valor': _as_number(value_diff),
        'Score descrição': _display_metric_number(score),
        'Regra ID': _display_rule_id(rule),
        'Motivo': _display_reason_motive(reason),
        'Ação manual': label,
    }


def _matched_side(item: object, frame: object, is_statement: bool, status: str, label: str) -> dict:
    '''Build single side row for matched pair.'''
    if is_statement:
        idx = item.get('statement_idx')
        origin = 'Extrato'
    else:
        idx = item.get('ledger_idx')
        origin = 'Interno'
    side = _extract_side(frame, idx)
    return _build_detail_dict(
        origin,
        side,
        status,
        item.get('match_id'),
        item.get('day_diff'),
        item.get('value_diff'),
        item.get('description_score'),
        item.get('rule_id'),
        item.get('reason'),
        label,
    )


def _single_side_rows(
    match_frame: object, statement_df: object, ledger_frame: object, status: str, manual: dict
) -> list:
    '''Build one row per pending duplicate entry.'''
    rows: list = []
    if match_frame is None or len(match_frame) == 0:
        return rows
    for _, item in match_frame.iterrows():
        rows.append(_single_side_row(item, statement_df, ledger_frame, status, manual))
    return rows


def _resolve_side_frame(item: object, statement_df: object, ledger_frame: object) -> tuple:
    '''Resolve index frame origin for single side row.'''
    source = item.get('source')
    if source == 'ledger':
        return (item.get('ledger_idx'), ledger_frame, 'Interno')
    if source == 'statement':
        return (item.get('statement_idx'), statement_df, 'Extrato')
    ledger_idx = item.get('ledger_idx')
    if ledger_idx is not None and not is_missing(ledger_idx):
        if source not in ('statement', 'ledger'):
            return (ledger_idx, ledger_frame, 'Interno')
    return (item.get('statement_idx'), statement_df, 'Extrato')


def _single_side_row(
    item: object, statement_df: object, ledger_frame: object, status: str, manual: dict
) -> dict:
    '''Build pending duplicate row resolving side.'''
    idx, frame, origin = _resolve_side_frame(item, statement_df, ledger_frame)
    side = _extract_side(frame, idx)
    pair = item.get('match_id')
    if pair is None or is_missing(pair):
        manual_entry: dict = {}
    else:
        manual_entry = manual.get(str(pair), {})
    return _single_row_dict(item, side, origin, status, pair, manual_entry)


def _single_row_dict(
    item: object, side: dict, origin: str, status: str, pair: object, manual_entry: dict
) -> dict:
    '''Build dict for single side detail row.'''
    return _build_detail_dict(
        origin,
        side,
        status,
        pair,
        item.get('day_diff'),
        item.get('value_diff'),
        item.get('description_score'),
        item.get('rule_id'),
        item.get('reason'),
        _manual_label(manual_entry.get('review_action', '')),
    )


def _collect_all_detail(
    results: dict, statement_df: object, ledger_frame: object, manual: dict
) -> dict:
    '''Collect detail rows for five categories.'''
    auto_rows = _matched_rows(
        results.get('auto'), statement_df, ledger_frame, _status_label('auto'), manual
    )
    potential_rows = _matched_rows(
        results.get('potential'), statement_df, ledger_frame, _status_label('potential'), manual
    )
    pending_rows = _single_side_rows(
        results.get('pending'), statement_df, ledger_frame, _status_label('pending'), manual
    )
    divergent_rows = _matched_rows(
        results.get('divergent'), statement_df, ledger_frame, _status_label('divergent'), manual
    )
    duplicate_rows = _single_side_rows(
        results.get('duplicate'), statement_df, ledger_frame, _status_label('duplicate'), manual
    )
    return {
        'auto': auto_rows,
        'potential': potential_rows,
        'pending': pending_rows,
        'divergent': divergent_rows,
        'duplicate': duplicate_rows,
    }
