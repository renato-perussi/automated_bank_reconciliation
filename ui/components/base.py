'''Display base wrappers for components.'''

import pandas as pd

from src.display import format_pct as _shared_pct
from src.display import lookup_value as _shared_lookup
from src.display import to_amount_text as _shared_amount
from src.display import to_date_text as _shared_date
from src.display import to_text as _shared_text
from src.money import clean_brl_text as _shared_clean_brl
from src.money import format_brl as _shared_brl


def format_pct(raw_value: object) -> str:
    '''Format percentage using pt-BR decimal comma.'''
    return _shared_pct(raw_value)


def format_brl(raw_value: object) -> str:
    '''Format numeric input as pt-BR currency text.'''
    return _shared_brl(raw_value)


def _lookup_field(source: pd.DataFrame, idx: object, fields: list) -> object:
    '''Return first available field value for index.'''
    found = _shared_lookup(source, idx, fields)
    return '—' if found is None else found


def side_triple(source: pd.DataFrame, idx: object) -> tuple:
    '''Extract date description amount triple for index.'''
    date_val = _lookup_field(source, idx, ['Data', 'event_date', 'normalized_date'])
    desc_val = _lookup_field(source, idx, ['Descrição', 'description', 'normalized_description'])
    amount_val = _lookup_field(
        source, idx, ['Valor', 'amount', 'normalized_value', 'normalized_amount']
    )
    return (date_val, desc_val, amount_val)


def _display_text(raw: object) -> str:
    '''Format cell value with empty fallback.'''
    return _shared_text(raw)


def _display_date(raw: object) -> str:
    '''Format date value as DD/MM/YYYY with fallback.'''
    return _shared_date(raw)


def _display_amount(raw: object) -> str:
    '''Format amount as BRL normalizing pt-BR input.'''
    return _shared_amount(raw)


def _normalize_amount_text(raw: object) -> object:
    '''Convert pt-BR money text to plain number text.'''
    return _shared_clean_brl(raw)


def _format_clean_amount(text: str) -> str:
    '''Format cleaned amount text with fallback.'''
    try:
        return format_brl(_normalize_amount_text(text))
    except (ValueError, TypeError):
        return text
