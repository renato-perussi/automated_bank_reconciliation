'''Side extraction for detail rows.'''

from src.display import lookup_value as _shared_lookup
from src.reporting.formatting import _as_number, _as_text, _format_iso


def _lookup_field(frame: object, idx: object, fields: list) -> object:
    '''Return first available field value for index.'''
    return _shared_lookup(frame, idx, fields)


def _extract_side(frame: object, idx: object) -> dict:
    '''Extract original normalized triple for index.'''
    orig_date = _lookup_field(frame, idx, ['Data', 'event_date'])
    norm_date = _lookup_field(frame, idx, ['normalized_date'])
    orig_desc = _lookup_field(frame, idx, ['Descrição', 'description'])
    orig_amount = _lookup_field(frame, idx, ['Valor', 'amount'])
    norm_value = _lookup_field(frame, idx, ['normalized_value', 'normalized_amount'])
    sign = _lookup_field(frame, idx, ['sign'])
    return {
        'orig_date': _as_text(orig_date),
        'norm_date': _format_iso(norm_date),
        'orig_desc': _as_text(orig_desc),
        'orig_amount': _as_text(orig_amount),
        'norm_value': _as_number(norm_value),
        'sign': _as_number(sign),
    }
