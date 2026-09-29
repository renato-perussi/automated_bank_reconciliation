'''Matching engine with blocking value sign and date window.'''

from bisect import bisect_left, bisect_right
from decimal import Decimal, InvalidOperation

import pandas as pd
from rapidfuzz import fuzz

from src.config import DATE_TOLERANCE_DAYS, FUZZY_THRESHOLD, MAX_ROWS_WARNING, VALUE_TOLERANCE
from src.logger import get_logger

logger = get_logger(__name__)


def build_params(
    date_tolerance_days: int = DATE_TOLERANCE_DAYS,
    fuzzy_threshold: int = FUZZY_THRESHOLD,
    value_tolerance: object = VALUE_TOLERANCE,
    use_fuzzy: bool = True,
) -> dict:
    '''Build validated engine params with pt-BR errors.'''
    _ensure_date_tolerance(date_tolerance_days)
    _ensure_fuzzy_threshold(fuzzy_threshold)
    clean_tolerance = _ensure_value_tolerance(value_tolerance)
    _ensure_use_fuzzy(use_fuzzy)
    return {
        'date_tolerance_days': date_tolerance_days,
        'fuzzy_threshold': fuzzy_threshold,
        'value_tolerance': clean_tolerance,
        'use_fuzzy': use_fuzzy,
    }


def _ensure_date_tolerance(value: object) -> None:
    '''Validate day window inside zero thirty range.'''
    if isinstance(value, bool):
        raise ValueError('Tolerância de dias deve estar entre 0 e 30.')
    if not isinstance(value, int):
        raise ValueError('Tolerância de dias deve estar entre 0 e 30.')
    if value < 0 or value > 30:
        raise ValueError('Tolerância de dias deve estar entre 0 e 30.')


def _ensure_fuzzy_threshold(value: object) -> None:
    '''Validate fuzzy threshold inside zero hundred range.'''
    if isinstance(value, bool):
        raise ValueError('Similaridade mínima deve estar entre 0 e 100.')
    if not isinstance(value, int):
        raise ValueError('Similaridade mínima deve estar entre 0 e 100.')
    if value < 0 or value > 100:
        raise ValueError('Similaridade mínima deve estar entre 0 e 100.')


def _ensure_value_tolerance(value: object) -> Decimal:
    '''Validate and convert value tolerance to Decimal.'''
    if isinstance(value, bool):
        raise ValueError('Tolerância de valor deve ser maior ou igual a 0.')
    try:
        clean = _convert_tolerance(value)
    except (InvalidOperation, ValueError, TypeError, AttributeError):
        raise ValueError('Tolerância de valor deve ser maior ou igual a 0.')
    if clean < Decimal('0'):
        raise ValueError('Tolerância de valor deve ser maior ou igual a 0.')
    return clean


def _convert_tolerance(value: object) -> Decimal:
    '''Convert tolerance input preserving exactness.'''
    if isinstance(value, Decimal):
        return value
    if isinstance(value, int):
        return Decimal(value)
    if isinstance(value, float):
        return Decimal(str(value))
    return Decimal(str(value))


def _ensure_use_fuzzy(value: object) -> None:
    '''Validate fuzzy flag is boolean.'''
    if not isinstance(value, bool):
        raise ValueError('Usar similaridade deve ser verdadeiro ou falso.')


def calc_value_diff(first: object, second: object) -> Decimal:
    '''Calculate absolute Decimal difference without float.'''
    first_dec = _to_decimal(first)
    second_dec = _to_decimal(second)
    return abs(first_dec - second_dec)


def _to_decimal(value: object) -> Decimal:
    '''Convert supported numeric input to Decimal.'''
    if isinstance(value, Decimal):
        return value
    if isinstance(value, bool):
        raise ValueError('Tolerância de valor deve ser maior ou igual a 0.')
    if isinstance(value, int):
        return Decimal(value)
    return Decimal(str(value))


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
    if value is None:
        return True
    try:
        result = pd.isna(value)
        if isinstance(result, bool):
            return result
        return bool(result)
    except (ValueError, TypeError):
        return False


def _has_error(row: pd.Series) -> bool:
    '''Detect non empty error code marking invalid row.'''
    if 'error_code' not in row.index:
        return False
    code = row['error_code']
    return isinstance(code, str) and code.strip() != ''


def _resolve_amount(row: pd.Series) -> object:
    '''Resolve Decimal amount preferring amount field.'''
    for field in ('normalized_amount', 'normalized_value'):
        if field not in row.index:
            continue
        value = row[field]
        if _is_missing(value):
            continue
        return value
    return None


def _resolve_entry_date(row: pd.Series) -> object:
    '''Resolve normalized date or none when missing.'''
    if 'normalized_date' not in row.index:
        return None
    value = row['normalized_date']
    if _is_missing(value):
        return None
    return value


def _resolve_entry_text(row: pd.Series) -> str:
    '''Resolve normalized description or empty string.'''
    if 'normalized_description' not in row.index:
        return ''
    value = row['normalized_description']
    if value is None:
        return ''
    try:
        if pd.isna(value):
            return ''
    except (ValueError, TypeError):
        pass
    return str(value)


def _resolve_entry_sign(row: pd.Series) -> object:
    '''Resolve integer sign or none when missing.'''
    if 'sign' not in row.index:
        return None
    value = row['sign']
    if _is_missing(value):
        return None
    try:
        return int(value)
    except (ValueError, TypeError):
        return None


def _collect_valid_entries(frame: pd.DataFrame) -> list:
    '''Collect valid entries with amount sign date text.'''
    entries: list = []
    for idx, row in frame.iterrows():
        if _has_error(row):
            continue
        amount = _resolve_amount(row)
        entry_date = _resolve_entry_date(row)
        sign = _resolve_entry_sign(row)
        if amount is None or entry_date is None or sign is None:
            continue
        if _is_missing(amount) or _is_missing(entry_date):
            continue
        entries.append(
            {
                'entry_idx': idx,
                'amount': amount,
                'entry_date': entry_date,
                'sign': sign,
                'entry_text': _resolve_entry_text(row),
            }
        )
    return entries


def _build_ledger_index(entries: list) -> dict:
    '''Build sign grouped sorted index for range lookup.'''
    grouped: dict = {}
    for entry in entries:
        grouped.setdefault(entry['sign'], []).append(entry)
    index: dict = {}
    for sign, items in grouped.items():
        ordered = sorted(items, key=lambda item: item['amount'])
        amounts = [item['amount'] for item in ordered]
        index[sign] = {'amounts': amounts, 'items': ordered}
    return index


def _find_window(amounts: list, items: list, target: object, tolerance: Decimal) -> list:
    '''Find indexed items inside amount tolerance window.'''
    low = target - tolerance
    high = target + tolerance
    left = bisect_left(amounts, low)
    right = bisect_right(amounts, high)
    return items[left:right]


def _calc_day_diff(first_date: object, second_date: object) -> int:
    '''Calculate absolute day difference for date likes.'''
    first_day = _to_day(first_date)
    second_day = _to_day(second_date)
    return abs((first_day - second_day).days)


def _to_day(value: object) -> object:
    '''Convert timestamp datetime date to plain date.'''
    if isinstance(value, pd.Timestamp):
        return value.date()
    result = getattr(value, 'date', None)
    if callable(result):
        try:
            return value.date()
        except (ValueError, TypeError):
            return value
    return value


def _warn_volume(statement_df: pd.DataFrame, ledger_df: pd.DataFrame) -> None:
    '''Warn pt-BR when volume may degrade performance.'''
    total = len(statement_df) + len(ledger_df)
    if total > MAX_ROWS_WARNING:
        logger.warning('Volume alto: resultado pode demorar.')
        return
    if len(statement_df) > MAX_ROWS_WARNING:
        logger.warning('Volume alto: resultado pode demorar.')
        return
    if len(ledger_df) > MAX_ROWS_WARNING:
        logger.warning('Volume alto: resultado pode demorar.')


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
