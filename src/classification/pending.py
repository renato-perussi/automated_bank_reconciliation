'''Pending rows with signal blocked check.'''

from decimal import Decimal, InvalidOperation

import pandas as pd

from src.classification.duplicates import _MATCH_COLUMNS, _empty_frame
from src.config import DATE_TOLERANCE_DAYS, VALUE_TOLERANCE
from src.entries import build_amount_index as _build_amount_index
from src.entries import collect_entries as _shared_collect
from src.entries import is_signal_blocked as _is_signal_blocked
from src.money import ensure_value_tolerance as _shared_ensure_tolerance


def _collect_simple_entries(frame: pd.DataFrame) -> list:
    '''Collect valid amount sign date entries for checks.'''
    raw = _shared_collect(frame)
    return [
        {
            'entry_idx': item['entry_idx'],
            'amount': item['amount'],
            'entry_date': item['entry_date'],
            'sign': item['sign'],
        }
        for item in raw
    ]


def _resolve_pending_limits(params: dict) -> tuple:
    '''Resolve tolerance and date limit for pending checks.'''
    tolerance = params.get('value_tolerance', VALUE_TOLERANCE)
    limit = params.get('date_tolerance_days', DATE_TOLERANCE_DAYS)
    if not isinstance(tolerance, Decimal):
        try:
            tolerance = _shared_ensure_tolerance(tolerance)
        except (ValueError, InvalidOperation, TypeError, AttributeError):
            tolerance = VALUE_TOLERANCE
    return (tolerance, limit)


def _collect_all_pending_rows(
    statement_df: pd.DataFrame,
    ledger_df: pd.DataFrame,
    params: dict,
    matched: tuple,
    statement_dups: set,
    ledger_dups: set,
    snapshot: dict,
) -> list:
    '''Collect pending rows from both bases with signal check.'''
    matched_statement, matched_ledger = matched
    statement_entries = _collect_simple_entries(statement_df)
    ledger_entries = _collect_simple_entries(ledger_df)
    statement_amounts, statement_ordered = _build_amount_index(statement_entries)
    ledger_amounts, ledger_ordered = _build_amount_index(ledger_entries)
    tolerance, limit = _resolve_pending_limits(params)
    rows = _pending_rows(
        statement_entries, ledger_amounts, ledger_ordered, matched_statement, statement_dups,
        'statement', tolerance, limit, snapshot,
    )
    rows.extend(
        _pending_rows(
            ledger_entries, statement_amounts, statement_ordered, matched_ledger, ledger_dups,
            'ledger', tolerance, limit, snapshot,
        )
    )
    return rows


def _build_pending_table(
    statement_df: pd.DataFrame,
    ledger_df: pd.DataFrame,
    params: dict,
    matched: tuple,
    statement_dups: set,
    ledger_dups: set,
    snapshot: dict,
) -> pd.DataFrame:
    '''Build pending table for unmatched valid rows.'''
    rows = _collect_all_pending_rows(
        statement_df, ledger_df, params, matched, statement_dups, ledger_dups, snapshot
    )
    if not rows:
        return _empty_frame()
    frame = pd.DataFrame(rows, columns=_MATCH_COLUMNS)
    return frame.sort_values(by=['source', 'statement_idx', 'ledger_idx']).reset_index(drop=True)


def _pending_rows(
    entries: list,
    other_amounts: list,
    other_ordered: list,
    matched_side: set,
    dups: set,
    source: str,
    tolerance: Decimal,
    limit: int,
    snapshot: dict,
) -> list:
    '''Build pending rows detecting signal blocked motive.'''
    rows: list = []
    for entry in entries:
        idx = entry['entry_idx']
        if idx in matched_side or idx in dups:
            continue
        if _is_signal_blocked(entry, other_amounts, other_ordered, tolerance, limit):
            rule = 'RN-03'
            reason = 'sinal_bloqueado'
        else:
            rule = 'RN-01'
            reason = 'sem_candidato'
        rows.append(_pending_row(idx, source, rule, reason, snapshot))
    return rows


def _pending_row(idx: object, source: str, rule: str, reason: str, snapshot: dict) -> dict:
    '''Build single pending row with empty match fields.'''
    if source == 'statement':
        first, second = idx, None
    else:
        first, second = None, idx
    return {
        'statement_idx': first,
        'ledger_idx': second,
        'match_id': None,
        'day_diff': None,
        'value_diff': None,
        'description_score': None,
        'rule_id': rule,
        'reason': reason,
        'params_snapshot': dict(snapshot),
        'source': source,
    }
