'''Pure display filters without streamlit.'''

from datetime import date, datetime

import pandas as pd


def filter_by_text(frame: pd.DataFrame, query: str) -> pd.DataFrame:
    '''Filter display rows by description substring.'''
    if frame is None or len(frame) == 0:
        return frame
    clean = str(query).strip().lower()
    if clean == '':
        return frame
    mask = pd.Series([False] * len(frame), index=frame.index)
    for field in ['Descrição', 'Descrição extrato', 'Descrição interno']:
        if field in frame.columns:
            part = frame[field].astype(str).str.lower().str.contains(clean, na=False)
            mask = mask | part
    return frame[mask]


def filter_by_value(frame: pd.DataFrame, low: float, high: float) -> pd.DataFrame:
    '''Filter display rows by numeric value window.'''
    if frame is None or len(frame) == 0:
        return frame
    fields = ['Valor', 'Valor extrato', 'Valor interno']
    present = [item for item in fields if item in frame.columns]
    if not present:
        return frame
    keep = pd.Series([False] * len(frame), index=frame.index)
    for field in present:
        numeric = pd.to_numeric(frame[field], errors='coerce')
        part = (numeric >= low) & (numeric <= high)
        part = part.fillna(True)
        keep = keep | part
    return frame[keep]


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
        part = dates.map(lambda item: item is not None and start <= item <= end)
        keep = keep | part.fillna(False)
    return frame[keep]


def value_bounds(display: pd.DataFrame) -> tuple:
    '''Infer slider bounds from display values.'''
    if display is None:
        return (0.0, 10000.0)
    try:
        if len(display) == 0:
            return (0.0, 10000.0)
        values: list = []
        for field in ['Valor', 'Valor extrato', 'Valor interno']:
            if field in display.columns:
                numeric = pd.to_numeric(display[field], errors='coerce').dropna()
                values.extend(numeric.tolist())
        if not values:
            return (0.0, 10000.0)
        low = float(min(values))
        high = float(max(values))
        if low == high:
            high = low + 1.0
        return (low, high)
    except (ValueError, TypeError):
        return (0.0, 10000.0)


def pending_bounds(left: pd.DataFrame, right: pd.DataFrame) -> tuple:
    '''Combine pending sides for slider bounds.'''
    if left is None or len(left) == 0:
        return value_bounds(right)
    if right is None or len(right) == 0:
        return value_bounds(left)
    try:
        combined = pd.concat([left, right], ignore_index=True)
    except (ValueError, TypeError):
        return value_bounds(left)
    return value_bounds(combined)


def safe_ratio(pct: float) -> float:
    '''Convert percentage to progress ratio.'''
    try:
        ratio = float(pct) / 100.0
    except (ValueError, TypeError):
        return 0.0
    if ratio < 0.0:
        return 0.0
    if ratio > 1.0:
        return 1.0
    return ratio
