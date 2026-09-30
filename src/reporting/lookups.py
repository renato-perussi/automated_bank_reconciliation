'''Side extraction for detail rows.'''

import pandas as pd

from src.reporting.formatting import _as_number, _as_text, _format_iso


def _lookup_field(frame: object, idx: object, fields: list) -> object:
    '''Return first available field value for index.'''
    if frame is None or idx is None:
        return None
    try:
        if len(frame) == 0 or idx not in frame.index:
            return None
        row = frame.loc[idx]
    except (KeyError, ValueError, TypeError):
        return None
    for field in fields:
        try:
            if field not in frame.columns:
                continue
            found = row[field]
        except (KeyError, ValueError):
            continue
        if found is None:
            continue
        try:
            if pd.isna(found):
                continue
        except (ValueError, TypeError):
            pass
        return found
    return None


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
