'''Date normalization to iso date.'''

import datetime

import pandas as pd

_DATE_PATTERNS = ('%d/%m/%Y', '%Y-%m-%d', '%d-%m-%Y')


def normalize_date(raw: object) -> tuple:
    '''Normalize raw date to iso date or invalid code.'''
    if raw is None:
        return None, 'DATA_INVALIDA'
    try:
        if pd.isna(raw):
            return None, 'DATA_INVALIDA'
    except (ValueError, TypeError):
        pass
    if isinstance(raw, pd.Timestamp):
        try:
            return raw.date(), None
        except ValueError:
            return None, 'DATA_INVALIDA'
    if isinstance(raw, datetime.datetime):
        return raw.date(), None
    if isinstance(raw, datetime.date):
        return raw, None
    if isinstance(raw, (int, float)):
        return None, 'DATA_INVALIDA'
    text = str(raw).strip()
    if text == '':
        return None, 'DATA_INVALIDA'
    parsed = _parse_date_text(text)
    if parsed is None:
        return None, 'DATA_INVALIDA'
    return parsed, None


def _parse_date_text(text: str) -> datetime.date | None:
    '''Try supported string patterns returning date or none.'''
    for pattern in _DATE_PATTERNS:
        try:
            return datetime.datetime.strptime(text, pattern).date()
        except ValueError:
            continue
    return None
