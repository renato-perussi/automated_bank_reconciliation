'''Temp app thin check.'''

import inspect

import app as mod


def test_app_has_no_dead_wrappers() -> None:
    '''Thin app keeps seven renders without dead shims.'''
    source = inspect.getsource(mod)
    assert source.count('render_') >= 7
    assert 'def filter_by_text' not in source
    assert 'def confirm_pair' not in source
