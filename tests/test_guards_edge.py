'''Guards edge branches for coverage.'''

from datetime import date, datetime

import numpy as np
import pandas as pd

from src.guards import (
    calc_day_diff,
    has_error_code,
    is_missing,
    safe_len,
    to_day,
    warn_volume,
)


def test_is_missing_none_nan_nat_na() -> None:
    '''None nan nat na count as missing.'''
    assert is_missing(None) is True
    assert is_missing(float('nan')) is True
    assert is_missing(pd.NA) is True
    assert is_missing(pd.NaT) is True
    assert is_missing('s0-l1') is False
    assert is_missing(3) is False


def test_is_missing_array_returns_false() -> None:
    '''Array isna raises value handled as not missing.'''
    assert is_missing(np.array([1, 2])) is False
    assert is_missing(np.array([np.nan])) is True


def test_has_error_code_variants() -> None:
    '''Error code detection across row shapes.'''
    good = pd.Series({'error_code': 'VALOR_INVALIDO'})
    assert has_error_code(good) is True
    empty = pd.Series({'error_code': '   '})
    assert has_error_code(empty) is False
    missing = pd.Series({'other': 'x'})
    assert has_error_code(missing) is False
    assert has_error_code(None) is False
    assert has_error_code('oops') is False
    assert has_error_code(42) is False


def test_to_day_timestamp_datetime_date() -> None:
    '''Timestamp datetime date normalize to date.'''
    stamp = pd.Timestamp('2026-09-10')
    assert to_day(stamp) == date(2026, 9, 10)
    moment = datetime(2026, 9, 10, 12, 30)
    assert to_day(moment) == date(2026, 9, 10)
    assert to_day(date(2026, 9, 10)) == date(2026, 9, 10)
    assert to_day('2026-09-10') == '2026-09-10'


def test_to_day_broken_date_returns_value() -> None:
    '''Broken date method falls back to value.'''

    class Broken:
        def date(self) -> object:
            raise ValueError('bad')

    target = Broken()
    assert to_day(target) is target


def test_calc_day_diff_uses_to_day() -> None:
    '''Day diff absolute across types.'''
    first = pd.Timestamp('2026-09-10')
    second = datetime(2026, 9, 12, 8, 0)
    assert calc_day_diff(first, second) == 2


def test_warn_volume_high_total_logs(caplog: object) -> None:
    '''Total above threshold warns once.'''
    import logging

    with caplog.at_level(logging.WARNING):
        warn_volume(20001, 0)
    assert any('Volume alto' in str(item.message) for item in caplog.records)


def test_warn_volume_single_frame_high_logs(caplog: object) -> None:
    '''Two frames above threshold warn via total.'''
    import logging

    first = pd.DataFrame([{'a': 1}] * 5)
    second = pd.DataFrame([{'a': 1}] * 5)
    with caplog.at_level(logging.WARNING):
        warn_volume(first, second, threshold=2)
    assert any('Volume alto' in str(item.message) for item in caplog.records)


def test_warn_volume_second_frame_high_logs(caplog: object) -> None:
    '''Int counts above threshold warn via total.'''
    import logging

    with caplog.at_level(logging.WARNING):
        warn_volume(5, 5, threshold=2)
    assert any('Volume alto' in str(item.message) for item in caplog.records)


def test_warn_volume_invalid_total_silent(caplog: object) -> None:
    '''Unmeasurable volume stays silent.'''
    import logging

    with caplog.at_level(logging.WARNING):
        warn_volume(None, None)
    assert all('Volume alto' not in str(item.message) for item in caplog.records)


def test_warn_volume_low_silent(caplog: object) -> None:
    '''Low volume stays silent.'''
    import logging

    with caplog.at_level(logging.WARNING):
        warn_volume(1, 1, threshold=20000)
    assert all('Volume alto' not in str(item.message) for item in caplog.records)


def test_safe_len_variants() -> None:
    '''None invalid frame sizes resolve safely.'''
    assert safe_len(None) == 0
    assert safe_len(pd.DataFrame([{'a': 1}, {'a': 2}])) == 2
    assert safe_len('oops') == 4
    assert safe_len(42) == 0
