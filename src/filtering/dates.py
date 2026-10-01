'''Date filtering for display rows.'''

from datetime import date, datetime

import pandas as pd


def parse_iso_date(text: str) -> object:
    '''Parse strict YYYY-MM-DD without dayfirst swap.'''
    iso = pd.to_datetime(text, format='%Y-%m-%d', errors='coerce')
    try:
        if pd.isna(iso):
            return None
    except (ValueError, TypeError):
        return None
    try:
        return iso.date()
    except (ValueError, TypeError, AttributeError):
        return None


def parse_filter_date(raw: object) -> object:
    '''Convert cell value to date tolerating errors.'''
    if raw is None:
        return None
    try:
        if pd.isna(raw):
            return None
    except (ValueError, TypeError):
        pass
    if isinstance(raw, pd.Timestamp):
        return raw.date()
    if isinstance(raw, datetime):
        return raw.date()
    if isinstance(raw, date):
        return raw
    text = str(raw).strip()
    if text == '' or text == '—':
        return None
    iso_date = parse_iso_date(text)
    if iso_date is not None:
        return iso_date
    parsed = pd.to_datetime(text, dayfirst=True, errors='coerce')
    try:
        if pd.isna(parsed):
            return None
    except (ValueError, TypeError):
        return None
    return parsed.date()


def normalize_period(period: object) -> tuple:
    '''Normalize date input to start end dates.'''
    if period is None:
        return (None, None)
    if isinstance(period, (list, tuple)):
        if len(period) == 0:
            return (None, None)
        if len(period) == 1:
            single = parse_filter_date(period[0])
            return (single, single)
        start = parse_filter_date(period[0])
        end = parse_filter_date(period[1])
        if start is not None and end is not None and end < start:
            return (end, start)
        return (start, end)
    single = parse_filter_date(period)
    return (single, single)


def filter_by_period(frame: pd.DataFrame, start: object, end: object) -> pd.DataFrame:
    '''Filter display rows by date window.'''
    if frame is None or len(frame) == 0:
        return frame
    if start is None and end is None:
        return frame
    if start is None:
        start = end
    if end is None:
        end = start
    fields = ['Data', 'Data extrato', 'Data interno']
    present = [item for item in fields if item in frame.columns]
    if not present:
        return frame
    keep = pd.Series([False] * len(frame), index=frame.index)
    for field in present:
        dates = frame[field].map(parse_filter_date)
        part = dates.map(lambda item: item is None or start <= item <= end)
        keep = keep | part.fillna(True)
    return frame[keep]
