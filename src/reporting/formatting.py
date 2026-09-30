'''Cell formatting without display fallback divergence.'''

from datetime import date, datetime

import pandas as pd

from src.money import as_number as _shared_as_number
from src.money import format_brl as _shared_format_brl


def format_brl(value: object) -> str:
    '''Format numeric input as pt-BR currency text.'''
    return _shared_format_brl(value)


def _format_iso(value: object) -> str:
    '''Format date like value as YYYY-MM-DD string.'''
    if value is None:
        return ''
    try:
        if pd.isna(value):
            return ''
    except (ValueError, TypeError):
        pass
    if isinstance(value, pd.Timestamp):
        return value.date().isoformat()
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    text = str(value).strip()
    if text == '' or text.lower() in ('nan', 'nat', 'none'):
        return ''
    return text


def _as_text(value: object) -> str:
    '''Convert cell value to stable text.'''
    if value is None:
        return ''
    try:
        if pd.isna(value):
            return ''
    except (ValueError, TypeError):
        pass
    if isinstance(value, pd.Timestamp):
        return value.strftime('%d/%m/%Y')
    if isinstance(value, datetime):
        return value.strftime('%d/%m/%Y')
    if isinstance(value, date):
        return value.strftime('%d/%m/%Y')
    return str(value)


def _as_number(value: object) -> object:
    '''Convert Decimal numeric to float preserving none.'''
    return _shared_as_number(value)


def _sort_number(value: object) -> object:
    '''Convert valor to sortable float keeping none last.'''
    number = _as_number(value)
    if number is None:
        return float('-inf')
    return float(number)
