'''Matching engine with blocking value sign and date window.'''

from decimal import Decimal

import pandas as pd
from rapidfuzz import fuzz

from src.config import DATE_TOLERANCE_DAYS, MAX_ROWS_WARNING, VALUE_TOLERANCE
from src.entries import build_ledger_index, collect_entries, find_amount_window, resolve_entry_text
from src.guards import calc_day_diff, warn_volume
from src.logger import get_logger
from src.money import calc_value_diff as _shared_value_diff
from src.money import ensure_value_tolerance
from src.params import build_params as _shared_build_params

logger = get_logger(__name__)

build_params = _shared_build_params

calc_value_diff = _shared_value_diff


def score_description(first: object, second: object) -> int:
    '''Score normalized descriptions with integer token set ratio.'''
    first_text = '' if first is None else str(first)
    second_text = '' if second is None else str(second)
    if first_text == '' and second_text == '':
        return 100
    if first_text == '' or second_text == '':
        return 0
    raw = fuzz.token_set_ratio(first_text, second_text)
    return int(round(raw))


def _lookup_texts(frame: pd.DataFrame) -> dict:
    '''Build index to normalized description lookup.'''
    lookup: dict = {}
    for idx, row in frame.iterrows():
        lookup[idx] = resolve_entry_text(row)
    return lookup


def _normalize_candidate(candidate: object) -> dict:
    '''Normalize tuple or dict candidate to dict form.'''
    if isinstance(candidate, dict):
        return dict(candidate)
    values = list(candidate)
    base = {
        'statement_idx': values[0] if len(values) > 0 else None,
        'ledger_idx': values[1] if len(values) > 1 else None,
        'day_diff': values[2] if len(values) > 2 else None,
        'value_diff': values[3] if len(values) > 3 else None,
    }
    if len(values) > 4:
        base['description_score'] = values[4]
    return base


def score_candidates(
    candidates: list, statement_df: pd.DataFrame, ledger_df: pd.DataFrame
) -> list:
    '''Attach description score to raw candidates deterministically.'''
    statement_texts = _lookup_texts(statement_df)
    ledger_texts = _lookup_texts(ledger_df)
    scored: list = []
    for candidate in candidates:
        item = _normalize_candidate(candidate)
        first_text = statement_texts.get(item.get('statement_idx'), '')
        second_text = ledger_texts.get(item.get('ledger_idx'), '')
        item['description_score'] = score_description(first_text, second_text)
        scored.append(item)
    scored.sort(key=lambda item: (str(item.get('statement_idx')), str(item.get('ledger_idx'))))
    return scored


def find_candidates(
    statement_df: pd.DataFrame, ledger_df: pd.DataFrame, params: dict
) -> list:
    '''Find scored candidates using blocking amount sign date.'''
    warn_volume(statement_df, ledger_df, MAX_ROWS_WARNING)
    date_limit = params.get('date_tolerance_days', DATE_TOLERANCE_DAYS)
    tolerance = params.get('value_tolerance', VALUE_TOLERANCE)
    if not isinstance(tolerance, Decimal):
        tolerance = ensure_value_tolerance(tolerance)
    statement_entries = collect_entries(statement_df)
    ledger_entries = collect_entries(ledger_df)
    ledger_index = build_ledger_index(ledger_entries)
    raw = _collect_raw_candidates(statement_entries, ledger_index, tolerance, date_limit)
    return score_candidates(raw, statement_df, ledger_df)


def _collect_raw_candidates(
    entries: list, ledger_index: dict, tolerance: Decimal, limit: int
) -> list:
    '''Collect raw pairs passing amount sign date filters.'''
    raw: list = []
    for entry in entries:
        bucket = ledger_index.get(entry['sign'])
        if not bucket:
            continue
        window = find_amount_window(
            bucket['amounts'], bucket['items'], entry['amount'], tolerance
        )
        for other in window:
            day_diff = calc_day_diff(entry['entry_date'], other['entry_date'])
            if day_diff > limit:
                continue
            value_diff = calc_value_diff(entry['amount'], other['amount'])
            if value_diff > tolerance:
                continue
            raw.append(
                {
                    'statement_idx': entry['entry_idx'],
                    'ledger_idx': other['entry_idx'],
                    'day_diff': day_diff,
                    'value_diff': value_diff,
                }
            )
    return raw
