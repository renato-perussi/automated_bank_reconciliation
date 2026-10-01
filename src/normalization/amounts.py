'''Amount normalization to Decimal.'''

import math
import re
from decimal import Decimal, InvalidOperation

import pandas as pd

from src.money import clean_brl_text as _shared_clean_brl_text
from src.normalization.signs import _has_credit_marker, _has_debit_marker, _resolve_amount_sign


def normalize_amount(raw: object) -> tuple:
    '''Normalize raw amount to Decimal or invalid code.'''
    if raw is None:
        return None, 'VALOR_INVALIDO'
    if isinstance(raw, bool):
        return None, 'VALOR_INVALIDO'
    if isinstance(raw, Decimal):
        return raw, None
    if isinstance(raw, int):
        return Decimal(raw), None
    if isinstance(raw, float):
        if math.isnan(raw) or math.isinf(raw):
            return None, 'VALOR_INVALIDO'
        try:
            return Decimal(str(raw)), None
        except InvalidOperation:
            return None, 'VALOR_INVALIDO'
    try:
        if pd.isna(raw):
            return None, 'VALOR_INVALIDO'
    except (ValueError, TypeError):
        pass
    text = str(raw).strip()
    if text == '':
        return None, 'VALOR_INVALIDO'
    return _parse_amount_text(text)


def _parse_amount_text(text: str) -> tuple:
    '''Parse amount string detecting sign and numeric core.'''
    upper = text.strip().upper()
    paren = '(' in upper and ')' in upper
    minus = '-' in upper
    plus = '+' in upper
    debit = _has_debit_marker(upper)
    credit = _has_credit_marker(upper)
    core = _clean_amount_core(upper)
    if core == '':
        return None, 'VALOR_INVALIDO'
    try:
        value = Decimal(core)
    except InvalidOperation:
        return None, 'VALOR_INVALIDO'
    sign = _resolve_amount_sign(paren, minus, plus, debit, credit)
    if sign < 0 and value > 0:
        value = -value
    return value, None


def _clean_amount_core(upper: str) -> str:
    '''Extract numeric core delegating marks to display cleaner.'''
    found = re.search(r'[\d\.,]+', upper)
    if not found:
        return ''
    return _shared_clean_brl_text(found.group(0))
