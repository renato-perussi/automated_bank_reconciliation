'''Temp display guards check.'''

from src.reporting.display_guards import blank_metric, blank_text


def test_blank_guards_unify_details_workbook() -> None:
    '''Blank helpers handle missing and values.'''
    import pandas as pd
    assert blank_text(None) == ''
    assert blank_text(float('nan')) == ''
    assert blank_text('s0-l1') == 's0-l1'
    assert blank_metric(None) == ''
    assert blank_metric(3) == 3
    assert blank_text(pd.NA) == ''
