'''Normalization of dates amounts and descriptions.'''

import datetime
import hashlib
import math
import re
import unicodedata
from decimal import Decimal, InvalidOperation

import pandas as pd

from src.logger import get_logger

logger = get_logger(__name__)

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


def _clean_amount_core(upper: str) -> str:
    '''Extract numeric core handling thousand and decimal marks.'''
    found = re.search(r'[\d\.,]+', upper)
    if not found:
        return ''
    core = found.group(0)
    if ',' in core:
        core = core.replace('.', '').replace(',', '.')
        return core
    if re.match(r'^\d{1,3}(\.\d{3})+$', core):
        return core.replace('.', '')
    return core


def detect_sign(normalized_value: object, raw_text: object) -> int | None:
    '''Detect debit or credit sign from value or raw markers.'''
    if isinstance(normalized_value, Decimal):
        if normalized_value < 0:
            return -1
        return 1
    if isinstance(normalized_value, (int, float)):
        try:
            if float(normalized_value) < 0:
                return -1
            return 1
        except (ValueError, TypeError):
            pass
    if normalized_value is not None:
        try:
            value = Decimal(str(normalized_value))
            if value < 0:
                return -1
            return 1
        except InvalidOperation:
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


def normalize_description(raw: object) -> str:
    '''Normalize description to canonical comparable form.'''
    if raw is None:
        return ''
    try:
        if pd.isna(raw):
            return ''
    except (ValueError, TypeError):
        pass
    text = str(raw).lower().strip()
    if text == '':
        return ''
    folded = unicodedata.normalize('NFKD', text)
    stripped = ''.join([c for c in folded if not unicodedata.combining(c)])
    cleaned = re.sub(r'[^a-z0-9\s]', '', stripped)
    return ' '.join(cleaned.split())


def normalize_table(frame: pd.DataFrame, source: str) -> pd.DataFrame:
    '''Normalize mapped table adding canonical fields and error code.'''
    result = frame.copy()
    dates: list = []
    amounts: list = []
    descs: list = []
    signs: list = []
    hashes: list = []
    errors: list = []
    for _, row in result.iterrows():
        values = _normalize_single_row(result, row)
        dates.append(values[0])
        amounts.append(values[1])
        descs.append(values[2])
        signs.append(values[3])
        hashes.append(values[4])
        errors.append(values[5])
    result['normalized_date'] = dates
    result['normalized_amount'] = amounts
    result['normalized_value'] = list(amounts)
    result['normalized_description'] = descs
    result['sign'] = signs
    result['row_hash'] = hashes
    result['source'] = [source] * len(result)
    result['error_code'] = errors
    logger.info(f'Normalized {len(result)} rows from {source}')
    return result


def _normalize_single_row(frame: pd.DataFrame, row: pd.Series) -> tuple:
    '''Normalize one row isolating failures without aborting batch.'''
    try:
        return _build_row_values(frame, row)
    except Exception as exc:
        logger.warning(f'Row normalization failed with {exc}')
        digest = _build_row_hash(None, None, '')
        return None, None, '', None, digest, 'VALOR_INVALIDO'


def _build_row_values(frame: pd.DataFrame, row: pd.Series) -> tuple:
    '''Build normalized values and hash for one row.'''
    cols = list(frame.columns)
    if 'event_date' not in cols or 'description' not in cols or 'amount' not in cols:
        digest = _build_row_hash(None, None, '')
        return None, None, '', None, digest, 'COLUNA_AUSENTE'
    raw_date = row['event_date']
    raw_desc = row['description']
    raw_amount = row['amount']
    norm_date, date_error = normalize_date(raw_date)
    norm_amount, amount_error = normalize_amount(raw_amount)
    norm_desc = normalize_description(raw_desc)
    sign = detect_sign(norm_amount, raw_amount)
    error = date_error if date_error is not None else amount_error
    digest = _build_row_hash(norm_date, norm_amount, norm_desc)
    return norm_date, norm_amount, norm_desc, sign, digest, error


def _build_row_hash(norm_date: object, norm_amount: object, norm_desc: str) -> str:
    '''Build deterministic sha256 hash for normalized row.'''
    date_part = '' if norm_date is None else str(norm_date)
    amount_part = '' if norm_amount is None else str(norm_amount)
    base = f'{date_part}|{amount_part}|{norm_desc}'
    return hashlib.sha256(base.encode('utf-8')).hexdigest()
