'''Sign detection for debit credit.'''

import re
from decimal import Decimal, InvalidOperation


def _resolve_amount_sign(paren: bool, minus: bool, plus: bool, debit: bool, credit: bool) -> int:
    '''Resolve sign with explicit marker precedence.'''
    if paren:
        return -1
    if minus:
        return -1
    if plus:
        return 1
    if debit:
        return -1
    if credit:
        return 1
    return 1


def _has_debit_marker(text: str) -> bool:
    '''Check debit markers as whole tokens.'''
    if re.search(r'\bD\b', text):
        return True
    if re.search(r'\bDEB\w*', text):
        return True
    if 'SAIDA' in text or 'SAÍDA' in text:
        return True
    if re.search(r'\bDEBITO\b', text) or re.search(r'\bDÉBITO\b', text):
        return True
    return False


def _has_credit_marker(text: str) -> bool:
    '''Check credit markers as whole tokens.'''
    if re.search(r'\bC\b', text):
        return True
    if re.search(r'\bCRED\w*', text):
        return True
    if 'ENTRADA' in text:
        return True
    if re.search(r'\bCREDITO\b', text) or re.search(r'\bCRÉDITO\b', text):
        return True
    return False


def _engine_sign_from_numeric(raw_numeric: object) -> int | None:
    '''Decide engine sign using Decimal without float.'''
    if isinstance(raw_numeric, bool):
        return None
    try:
        amount = Decimal(str(raw_numeric))
    except (InvalidOperation, ValueError, TypeError, AttributeError):
        return None
    if amount < 0:
        return -1
    return 1


def detect_sign(normalized_value: object, raw_text: object) -> int | None:
    '''Detect debit or credit sign from Decimal engine value or raw markers.'''
    if isinstance(normalized_value, Decimal):
        if normalized_value < 0:
            return -1
        return 1
    if isinstance(normalized_value, (int, float)) and not isinstance(normalized_value, bool):
        decided = _engine_sign_from_numeric(normalized_value)
        if decided is not None:
            return decided
    if normalized_value is not None:
        try:
            value = Decimal(str(normalized_value))
            if value < 0:
                return -1
            return 1
        except (InvalidOperation, ValueError, TypeError, AttributeError):
            pass
    text = '' if raw_text is None else str(raw_text).upper()
    return _infer_sign_from_text(text)


def _infer_sign_from_text(text: str) -> int | None:
    '''Infer sign from raw markers with explicit precedence.'''
    if '(' in text and ')' in text:
        return -1
    if '-' in text:
        return -1
    if '+' in text:
        return 1
    if _has_debit_marker(text):
        return -1
    if _has_credit_marker(text):
        return 1
    return None
