'''Shared pandas missing day and volume guards.'''

import pandas as pd

from src.config import MAX_ROWS_WARNING
from src.logger import get_logger

logger = get_logger(__name__)


def is_missing(value: object) -> bool:
    '''Check pandas aware missing value.'''
    if value is None:
        return True
    try:
        result = pd.isna(value)
        if isinstance(result, bool):
            return result
        return bool(result)
    except (ValueError, TypeError):
        return False


def has_error_code(row: object) -> bool:
    '''Detect non empty error code marking invalid row.'''
    try:
        if 'error_code' not in row.index:
            return False
        code = row['error_code']
    except (AttributeError, KeyError, TypeError):
        return False
    return isinstance(code, str) and code.strip() != ''


def to_day(value: object) -> object:
    '''Convert timestamp datetime date to plain date.'''
    if isinstance(value, pd.Timestamp):
        return value.date()
    result = getattr(value, 'date', None)
    if callable(result):
        try:
            return value.date()
        except (ValueError, TypeError):
            return value
    return value


def calc_day_diff(first_date: object, second_date: object) -> int:
    '''Calculate absolute day difference for date likes.'''
    first_day = to_day(first_date)
    second_day = to_day(second_date)
    return abs((first_day - second_day).days)


def warn_volume(
    statement_df: object, ledger_df: object, threshold: int = MAX_ROWS_WARNING
) -> None:
    '''Warn pt-BR when volume may degrade performance.'''
    total = _volume_total(statement_df, ledger_df)
    if total is None:
        return
    if total > threshold:
        logger.warning('Volume alto: resultado pode demorar.')
        return
    first = _volume_size(statement_df)
    second = _volume_size(ledger_df)
    if first is not None and first > threshold:
        logger.warning('Volume alto: resultado pode demorar.')
        return
    if second is not None and second > threshold:
        logger.warning('Volume alto: resultado pode demorar.')


def _volume_total(first: object, second: object) -> object:
    '''Sum sizes handling frames and counts.'''
    try:
        return len(first) + len(second)
    except TypeError:
        pass
    try:
        return int(first) + int(second)
    except (ValueError, TypeError):
        return None


def _volume_size(value: object) -> object:
    '''Return size handling frames and counts.'''
    try:
        return int(len(value))
    except TypeError:
        pass
    try:
        return int(value)
    except (ValueError, TypeError):
        return None


def safe_len(frame: object) -> int:
    '''Return row count handling none.'''
    if frame is None:
        return 0
    try:
        return int(len(frame))
    except TypeError:
        return 0
