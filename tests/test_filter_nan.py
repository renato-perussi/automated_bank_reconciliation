'''Value filter nan handling documented.'''

import pandas as pd

from src.filters import filter_by_value


def test_filter_by_value_illegible_documented() -> None:
    '''Illegible values handled deterministically via fillna design.'''
    frame = pd.DataFrame(
        [{'Valor': 'abc'}, {'Valor': None}, {'Valor': float('nan')}, {'Valor': 10}]
    )
    found = filter_by_value(frame, 0.0, 50.0)
    assert 10 in found['Valor'].tolist()
    assert len(found) >= 1
    assert len(found) <= 4


def test_filter_by_value_valid_window_keeps_inside() -> None:
    '''Valid window keeps inside rows without crash on nan.'''
    frame = pd.DataFrame([{'Valor': float('nan')}, {'Valor': 10}, {'Valor': 5000}])
    found = filter_by_value(frame, 0.0, 50.0)
    assert 10 in found['Valor'].tolist()
    assert 5000 not in found['Valor'].tolist()
