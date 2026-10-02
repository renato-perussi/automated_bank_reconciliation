'''Blank guards for report detail and log cells.'''

from src.guards import is_missing


def blank_text(raw: object) -> str:
    '''Return blank for missing pandas text else raw.'''
    if raw is None:
        return ''
    if is_missing(raw):
        return ''
    return raw


def blank_metric(raw: object) -> object:
    '''Return blank for missing pandas metric else raw.'''
    if raw is None:
        return ''
    if is_missing(raw):
        return ''
    return raw
