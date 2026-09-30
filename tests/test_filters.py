'''Filter helpers red-green tests.'''

from datetime import date

import pandas as pd


def test_filter_by_text_matches_description() -> None:
    '''Substring search keeps matching rows.'''
    from src.filters import filter_by_text
    frame = pd.DataFrame([{'Descrição': 'Pagamento Fornecedor X'}])
    found = filter_by_text(frame, 'fornecedor')
    assert len(found) == 1


def test_filter_by_text_empty_query_returns_all() -> None:
    '''Empty query keeps every row.'''
    from src.filters import filter_by_text
    frame = pd.DataFrame([{'Descrição': 'Alpha'}, {'Descrição': 'Beta'}])
    found = filter_by_text(frame, '   ')
    assert len(found) == 2


def test_filter_by_value_window() -> None:
    '''Value window keeps inside rows.'''
    from src.filters import filter_by_value
    frame = pd.DataFrame([{'Valor': 100}, {'Valor': 5000}])
    found = filter_by_value(frame, 0.0, 1000.0)
    assert len(found) == 1


def test_filter_by_period_window() -> None:
    '''Date window keeps inside rows.'''
    from src.filters import filter_by_period
    frame = pd.DataFrame([{'Data': '10/09/2026'}, {'Data': '20/09/2026'}])
    start = date(2026, 9, 9)
    end = date(2026, 9, 11)
    found = filter_by_period(frame, start, end)
    assert len(found) == 1


def test_parse_filter_date_invalid_returns_none() -> None:
    '''Invalid text yields none.'''
    from src.filters import parse_filter_date
    assert parse_filter_date('—') is None
    assert parse_filter_date(None) is None


def test_normalize_period_swaps_inverted() -> None:
    '''Inverted range returns ordered bounds.'''
    from src.filters import normalize_period
    start = date(2026, 9, 20)
    end = date(2026, 9, 10)
    ordered_start, ordered_end = normalize_period((start, end))
    assert ordered_start <= ordered_end


def test_value_bounds_single_value_expands() -> None:
    '''Equal bounds expand by one.'''
    from src.filters import value_bounds
    frame = pd.DataFrame([{'Valor': 100}])
    low, high = value_bounds(frame)
    assert high == low + 1.0


def test_pending_bounds_empty_left_uses_right() -> None:
    '''Empty left delegates to right bounds.'''
    from src.filters import pending_bounds, value_bounds
    right = pd.DataFrame([{'Valor': 250}])
    assert pending_bounds(pd.DataFrame(), right) == value_bounds(right)


def test_safe_ratio_clamps() -> None:
    '''Out of range ratios clamp.'''
    from src.filters import safe_ratio
    assert safe_ratio(150.0) == 1.0
    assert safe_ratio(-5.0) == 0.0
    assert safe_ratio('bad') == 0.0


def test_filter_by_text_none_empty_no_column() -> None:
    '''None empty missing column keep safe.'''
    from src.filters import filter_by_text
    assert filter_by_text(None, 'x') is None
    empty = pd.DataFrame()
    assert len(filter_by_text(empty, 'x')) == 0
    other = pd.DataFrame([{'Outro': 'abc'}])
    assert len(filter_by_text(other, 'abc')) == 0
    assert len(filter_by_text(other, '')) == 1


def test_filter_by_value_none_no_present() -> None:
    '''None empty unknown columns keep safe.'''
    from src.filters import filter_by_value
    assert filter_by_value(None, 0.0, 1.0) is None
    assert len(filter_by_value(pd.DataFrame(), 0.0, 1.0)) == 0
    other = pd.DataFrame([{'Outro': 5}])
    assert len(filter_by_value(other, 0.0, 10.0)) == 1


def test_parse_filter_date_variants() -> None:
    '''Timestamp datetime date empty invalid parse.'''
    from datetime import datetime

    import pandas as pd

    from src.filters import parse_filter_date
    assert parse_filter_date(pd.Timestamp('2026-09-10')) == date(2026, 9, 10)
    assert parse_filter_date(datetime(2026, 9, 10, 12, 0)) == date(2026, 9, 10)
    assert parse_filter_date(date(2026, 9, 10)) == date(2026, 9, 10)
    assert parse_filter_date('') is None
    assert parse_filter_date('nonsense-xyz') is None
    assert parse_filter_date(float('nan')) is None


def test_normalize_period_variants() -> None:
    '''None empty single date object normalize.'''
    from src.filters import normalize_period
    assert normalize_period(None) == (None, None)
    assert normalize_period([]) == (None, None)
    single = date(2026, 9, 10)
    assert normalize_period([single]) == (single, single)
    assert normalize_period(single) == (single, single)
    assert normalize_period((single, single)) == (single, single)


def test_filter_by_period_edges() -> None:
    '''None bounds single side no columns safe.'''
    from src.filters import filter_by_period
    frame = pd.DataFrame([{'Data': '10/09/2026'}])
    assert filter_by_period(None, None, None) is None
    assert len(filter_by_period(frame, None, None)) == 1
    start = date(2026, 9, 9)
    assert len(filter_by_period(frame, None, start)) == 0
    assert len(filter_by_period(frame, start, None)) == 0
    other = pd.DataFrame([{'Outro': 'x'}])
    assert len(filter_by_period(other, start, start)) == 1


def test_value_pending_bounds_edges() -> None:
    '''None empty no values combined bounds.'''
    from src.filters import pending_bounds, value_bounds
    assert value_bounds(None) == (0.0, 10000.0)
    assert value_bounds(pd.DataFrame()) == (0.0, 10000.0)
    assert value_bounds(pd.DataFrame([{'Outro': 1}])) == (0.0, 10000.0)
    left = pd.DataFrame([{'Valor': 10}])
    right = pd.DataFrame([{'Valor': 90}])
    low, high = pending_bounds(left, right)
    assert low == 10.0
    assert high == 90.0
    assert pending_bounds(left, pd.DataFrame()) == value_bounds(left)


def test_safe_ratio_valid() -> None:
    '''Valid percent converts to ratio.'''
    from src.filters import safe_ratio
    assert safe_ratio(50.0) == 0.5
    assert safe_ratio(0) == 0.0
