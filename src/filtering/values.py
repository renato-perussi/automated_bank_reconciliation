'''Value filtering for display rows.'''

import pandas as pd

from src.money import parse_display_number


def parse_amount_number(raw: object) -> object:
    '''Parse pt-BR BRL display text to display float for filters.'''
    try:
        if pd.isna(raw):
            return None
    except (ValueError, TypeError):
        pass
    return parse_display_number(raw)


def filter_by_value(frame: pd.DataFrame, low: float, high: float) -> pd.DataFrame:
    '''Filter display rows by display float value window.'''
    if frame is None or len(frame) == 0:
        return frame
    fields = ['Valor', 'Valor extrato', 'Valor interno']
    present = [item for item in fields if item in frame.columns]
    if not present:
        return frame
    keep = pd.Series([False] * len(frame), index=frame.index)
    for field in present:
        numeric = frame[field].map(parse_amount_number)
        numeric = pd.to_numeric(numeric, errors='coerce')
        part = (numeric >= low) & (numeric <= high)
        part = part.fillna(True)
        keep = keep | part
    return frame[keep]
