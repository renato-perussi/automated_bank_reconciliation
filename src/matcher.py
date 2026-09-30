'''Matching engine with blocking value sign and date window.'''

from decimal import Decimal

import pandas as pd
from rapidfuzz import fuzz

from src.config import DATE_TOLERANCE_DAYS, FUZZY_THRESHOLD, MAX_ROWS_WARNING, VALUE_TOLERANCE
from src.entries import build_ledger_index as _shared_ledger_index
from src.entries import collect_entries as _shared_collect
from src.entries import find_amount_window as _shared_window
from src.entries import resolve_amount as _shared_resolve_amount
from src.entries import resolve_entry_date as _shared_resolve_date
from src.entries import resolve_entry_sign as _shared_resolve_sign
from src.entries import resolve_entry_text as _shared_resolve_text
from src.guards import calc_day_diff as _shared_day_diff
from src.guards import has_error_code as _shared_has_error
from src.guards import is_missing as _shared_is_missing
from src.guards import to_day as _shared_to_day
from src.guards import warn_volume as _shared_warn_volume
from src.logger import get_logger
from src.money import calc_value_diff as _shared_value_diff
from src.money import convert_tolerance as _shared_convert
from src.money import ensure_value_tolerance as _shared_ensure_tolerance
from src.money import to_decimal as _shared_to_decimal
from src.params import build_params as _shared_build_params
from src.params import ensure_date_tolerance as _shared_ensure_date
from src.params import ensure_fuzzy_threshold as _shared_ensure_fuzzy
from src.params import ensure_use_fuzzy as _shared_ensure_flag

logger = get_logger(__name__)


def build_params(
    date_tolerance_days: int = DATE_TOLERANCE_DAYS,
    fuzzy_threshold: int = FUZZY_THRESHOLD,
    value_tolerance: object = VALUE_TOLERANCE,
    use_fuzzy: bool = True,
) -> dict:
    '''Build validated engine params with pt-BR errors.'''
    return _shared_build_params(
        date_tolerance_days, fuzzy_threshold, value_tolerance, use_fuzzy
    )


def _ensure_date_tolerance(value: object) -> None:
    '''Validate day window inside zero thirty range.'''
    _shared_ensure_date(value)


def _ensure_fuzzy_threshold(value: object) -> None:
    '''Validate fuzzy threshold inside zero hundred range.'''
    _shared_ensure_fuzzy(value)


def _ensure_value_tolerance(value: object) -> Decimal:
    '''Validate and convert value tolerance to Decimal.'''
    return _shared_ensure_tolerance(value)


def _convert_tolerance(value: object) -> Decimal:
    '''Convert tolerance input preserving exactness.'''
    return _shared_convert(value)


def _ensure_use_fuzzy(value: object) -> None:
    '''Validate fuzzy flag is boolean.'''
    _shared_ensure_flag(value)


def calc_value_diff(first: object, second: object) -> Decimal:
    '''Calculate absolute Decimal difference without float.'''
    return _shared_value_diff(first, second)


def _to_decimal(value: object) -> Decimal:
    '''Convert supported numeric input to Decimal.'''
    return _shared_to_decimal(value)


def score_description(first: object, second: object) -> int:
    '''Score normalized descriptions with token set ratio.'''
    first_text = '' if first is None else str(first)
    second_text = '' if second is None else str(second)
    if first_text == '' and second_text == '':
        return 100
    if first_text == '' or second_text == '':
        return 0
    raw = fuzz.token_set_ratio(first_text, second_text)
    return int(round(float(raw)))


def _is_missing(value: object) -> bool:
    '''Check pandas aware missing value.'''
    return _shared_is_missing(value)


def _has_error(row: pd.Series) -> bool:
    '''Detect non empty error code marking invalid row.'''
    return _shared_has_error(row)


def _resolve_amount(row: pd.Series) -> object:
    '''Resolve Decimal amount preferring amount field.'''
    return _shared_resolve_amount(row)


def _resolve_entry_date(row: pd.Series) -> object:
    '''Resolve normalized date or none when missing.'''
    return _shared_resolve_date(row)


def _resolve_entry_text(row: pd.Series) -> str:
    '''Resolve normalized description or empty string.'''
    return _shared_resolve_text(row)


def _resolve_entry_sign(row: pd.Series) -> object:
    '''Resolve integer sign or none when missing.'''
    return _shared_resolve_sign(row)


def _collect_valid_entries(frame: pd.DataFrame) -> list:
    '''Collect valid entries with amount sign date text.'''
    return _shared_collect(frame)


def _build_ledger_index(entries: list) -> dict:
    '''Build sign grouped sorted index for range lookup.'''
    return _shared_ledger_index(entries)


def _find_window(amounts: list, items: list, target: object, tolerance: Decimal) -> list:
    '''Find indexed items inside amount tolerance window.'''
    return _shared_window(amounts, items, target, tolerance)


def _calc_day_diff(first_date: object, second_date: object) -> int:
    '''Calculate absolute day difference for date likes.'''
    return _shared_day_diff(first_date, second_date)


def _to_day(value: object) -> object:
    '''Convert timestamp datetime date to plain date.'''
    return _shared_to_day(value)


def _warn_volume(statement_df: pd.DataFrame, ledger_df: pd.DataFrame) -> None:
    '''Warn pt-BR when volume may degrade performance.'''
    _shared_warn_volume(statement_df, ledger_df, MAX_ROWS_WARNING)


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


def _lookup_texts(frame: pd.DataFrame) -> dict:
    '''Build index to normalized description lookup.'''
    lookup: dict = {}
    for idx, row in frame.iterrows():
        lookup[idx] = _resolve_entry_text(row)
    return lookup


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
    _warn_volume(statement_df, ledger_df)
    date_limit = params.get('date_tolerance_days', DATE_TOLERANCE_DAYS)
    tolerance = params.get('value_tolerance', VALUE_TOLERANCE)
    if not isinstance(tolerance, Decimal):
        tolerance = _ensure_value_tolerance(tolerance)
    statement_entries = _collect_valid_entries(statement_df)
    ledger_entries = _collect_valid_entries(ledger_df)
    ledger_index = _build_ledger_index(ledger_entries)
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
        window = _find_window(bucket['amounts'], bucket['items'], entry['amount'], tolerance)
        for other in window:
            day_diff = _calc_day_diff(entry['entry_date'], other['entry_date'])
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
