'''Export service bytes tests.'''

import pandas as pd

from src.matcher import build_params


def test_build_export_bytes_empty_results() -> None:
    '''Empty tables yield xlsx and csv bytes.'''
    from src.export_service import build_export_bytes
    empty = pd.DataFrame()
    results = {
        'auto': empty,
        'potential': empty,
        'pending': empty,
        'divergent': empty,
        'duplicate': empty,
    }
    excel_bytes, csv_bytes = build_export_bytes(
        results, build_params(), empty, empty, empty, empty, []
    )
    assert isinstance(excel_bytes, bytes)
    assert len(excel_bytes) > 0
    assert isinstance(csv_bytes, bytes)
    assert 'Par ID' in csv_bytes.decode('utf-8')
