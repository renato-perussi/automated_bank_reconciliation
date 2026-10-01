'''Shared display conversions for ui and reports.'''

from datetime import date, datetime

import pandas as pd

from src.money import clean_brl_text as _clean_text
from src.money import format_brl as _format_money


def lookup_value(frame: object, idx: object, fields: list) -> object:
    '''Return first available field value for index.'''
    if frame is None or idx is None:
        return None
    try:
        if len(frame) == 0 or idx not in frame.index:
            return None
        row = frame.loc[idx]
    except (KeyError, ValueError, TypeError):
        return None
    for field in fields:
        try:
            if field not in frame.columns:
                continue
            found = row[field]
        except (KeyError, ValueError):
            continue
        if found is None:
            continue
        try:
            if pd.isna(found):
                continue
        except (ValueError, TypeError):
            pass
        return found
    return None


def to_text(raw: object, missing: str = '—') -> str:
    '''Convert cell value to display text.'''
    if raw is None:
        return missing
    try:
        if pd.isna(raw):
            return missing
    except (ValueError, TypeError):
        pass
    if isinstance(raw, pd.Timestamp):
        return raw.strftime('%d/%m/%Y')
    if isinstance(raw, datetime):
        return raw.strftime('%d/%m/%Y')
    if isinstance(raw, date):
        return raw.strftime('%d/%m/%Y')
    text = str(raw).strip()
    if text == '' or text == '—' or text.lower() in ('nan', 'nat', 'none'):
        return missing
    return text


def to_report_text(raw: object) -> str:
    '''Convert cell value to report text.'''
    if raw is None:
        return ''
    try:
        if pd.isna(raw):
            return ''
    except (ValueError, TypeError):
        pass
    if isinstance(raw, pd.Timestamp):
        return raw.strftime('%d/%m/%Y')
    if isinstance(raw, datetime):
        return raw.strftime('%d/%m/%Y')
    if isinstance(raw, date):
        return raw.strftime('%d/%m/%Y')
    return str(raw)


def to_iso_text(raw: object) -> str:
    '''Format date like value as iso text.'''
    if raw is None:
        return ''
    try:
        if pd.isna(raw):
            return ''
    except (ValueError, TypeError):
        pass
    if isinstance(raw, pd.Timestamp):
        return raw.date().isoformat()
    if isinstance(raw, datetime):
        return raw.date().isoformat()
    if isinstance(raw, date):
        return raw.isoformat()
    text = str(raw).strip()
    if text == '' or text.lower() in ('nan', 'nat', 'none'):
        return ''
    return text


def to_date_text(raw: object, missing: str = '—') -> str:
    '''Format date value as display date.'''
    text = to_text(raw, missing)
    if text == missing:
        return text
    try:
        return pd.to_datetime(text, format='%Y-%m-%d').strftime('%d/%m/%Y')
    except (ValueError, TypeError):
        pass
    try:
        parsed = pd.to_datetime(text, dayfirst=True, errors='coerce')
        if pd.isna(parsed):
            return text
        return parsed.strftime('%d/%m/%Y')
    except (ValueError, TypeError):
        return text


def to_amount_text(raw: object, missing: str = '—') -> str:
    '''Format amount value as display money.'''
    if raw is None:
        return missing
    try:
        if pd.isna(raw):
            return missing
    except (ValueError, TypeError):
        pass
    text = str(raw).strip()
    if text == '' or text.lower() in ('nan', 'nat', 'none', '—'):
        return missing
    try:
        return _format_money(_clean_text(text))
    except (ValueError, TypeError):
        return text


def format_pct(raw_value: object) -> str:
    '''Format percentage using decimal comma.'''
    try:
        text = f'{float(raw_value):.1f}'
    except (ValueError, TypeError):
        return '—'
    return f'{text.replace(".", ",")}%'
