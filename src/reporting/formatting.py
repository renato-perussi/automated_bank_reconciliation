'''Cell formatting without display fallback divergence.'''

from src.display import to_iso_text as _shared_iso
from src.display import to_report_text as _shared_text
from src.money import as_number as _shared_as_number
from src.money import format_brl as _shared_format_brl

format_brl = _shared_format_brl

_as_number = _shared_as_number


def _format_iso(value: object) -> str:
    '''Format date like value as YYYY-MM-DD string.'''
    return _shared_iso(value)


def _as_text(value: object) -> str:
    '''Convert cell value to stable text.'''
    return _shared_text(value)


def _sort_number(value: object) -> object:
    '''Convert valor to display sortable float keeping none last.'''
    number = _as_number(value)
    if number is None:
        return float('-inf')
    return float(number)
