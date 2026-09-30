'''Shared engine params validation and snapshot.'''

from decimal import Decimal

from src.config import APP_VERSION, DATE_TOLERANCE_DAYS, FUZZY_THRESHOLD, VALUE_TOLERANCE
from src.money import ensure_value_tolerance


def build_params(
    date_tolerance_days: int = DATE_TOLERANCE_DAYS,
    fuzzy_threshold: int = FUZZY_THRESHOLD,
    value_tolerance: object = VALUE_TOLERANCE,
    use_fuzzy: bool = True,
) -> dict:
    '''Build validated engine params with pt-BR errors.'''
    ensure_date_tolerance(date_tolerance_days)
    ensure_fuzzy_threshold(fuzzy_threshold)
    clean_tolerance = ensure_value_tolerance(value_tolerance)
    ensure_use_fuzzy(use_fuzzy)
    return {
        'date_tolerance_days': date_tolerance_days,
        'fuzzy_threshold': fuzzy_threshold,
        'value_tolerance': clean_tolerance,
        'use_fuzzy': use_fuzzy,
    }


def ensure_date_tolerance(value: object) -> None:
    '''Validate day window inside zero thirty range.'''
    if isinstance(value, bool):
        raise ValueError('Tolerância de dias deve estar entre 0 e 30.')
    if not isinstance(value, int):
        raise ValueError('Tolerância de dias deve estar entre 0 e 30.')
    if value < 0 or value > 30:
        raise ValueError('Tolerância de dias deve estar entre 0 e 30.')


def ensure_fuzzy_threshold(value: object) -> None:
    '''Validate fuzzy threshold inside zero hundred range.'''
    if isinstance(value, bool):
        raise ValueError('Similaridade mínima deve estar entre 0 e 100.')
    if not isinstance(value, int):
        raise ValueError('Similaridade mínima deve estar entre 0 e 100.')
    if value < 0 or value > 100:
        raise ValueError('Similaridade mínima deve estar entre 0 e 100.')


def ensure_use_fuzzy(value: object) -> None:
    '''Validate fuzzy flag is boolean.'''
    if not isinstance(value, bool):
        raise ValueError('Usar similaridade deve ser verdadeiro ou falso.')


def params_snapshot(params: object) -> dict:
    '''Build deterministic snapshot with app version.'''
    base = {} if not isinstance(params, dict) else dict(params)
    tolerance = base.get('value_tolerance', VALUE_TOLERANCE)
    if not isinstance(tolerance, Decimal):
        try:
            tolerance = Decimal(str(tolerance))
        except Exception:
            tolerance = VALUE_TOLERANCE
    version = base.get('APP_VERSION', base.get('app_version', APP_VERSION))
    return {
        'date_tolerance_days': base.get('date_tolerance_days', DATE_TOLERANCE_DAYS),
        'fuzzy_threshold': base.get('fuzzy_threshold', FUZZY_THRESHOLD),
        'value_tolerance': tolerance,
        'use_fuzzy': base.get('use_fuzzy', True),
        'APP_VERSION': str(version),
    }


def snapshot_text(snapshot: dict) -> str:
    '''Render snapshot as single audit string.'''
    day = snapshot.get('date_tolerance_days')
    fuzzy = snapshot.get('fuzzy_threshold')
    tolerance = snapshot.get('value_tolerance')
    version = snapshot.get('APP_VERSION', snapshot.get('app_version', APP_VERSION))
    first = f'date_tolerance_days={day}; fuzzy_threshold={fuzzy}'
    second = f'value_tolerance={tolerance}; APP_VERSION={version}'
    return f'{first}; {second}'


def infer_params(results: object) -> dict:
    '''Infer params snapshot from first available row.'''
    if not isinstance(results, dict):
        return {}
    for key in ('auto', 'potential', 'pending', 'divergent', 'duplicate'):
        frame = results.get(key)
        try:
            has_rows = frame is not None and len(frame) > 0
            has_col = 'params_snapshot' in list(frame.columns)
        except (TypeError, AttributeError):
            continue
        if has_rows and has_col:
            first = frame.iloc[0]['params_snapshot']
            if isinstance(first, dict):
                return dict(first)
    return {}
