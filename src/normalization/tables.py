'''Table orchestration for normalized rows.'''

import hashlib
from decimal import InvalidOperation

import pandas as pd

from src.logger import get_logger
from src.normalization.amounts import normalize_amount
from src.normalization.dates import normalize_date
from src.normalization.descriptions import normalize_description
from src.normalization.signs import detect_sign

logger = get_logger(__name__)


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
    except (ValueError, TypeError, AttributeError, InvalidOperation, KeyError) as exc:
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
