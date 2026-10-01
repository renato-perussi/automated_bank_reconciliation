'''Text filtering for display rows.'''

import pandas as pd


def filter_by_text(frame: pd.DataFrame, query: str) -> pd.DataFrame:
    '''Filter display rows by description substring.'''
    if frame is None or len(frame) == 0:
        return frame
    clean = str(query).strip().lower()
    if clean == '':
        return frame
    mask = pd.Series([False] * len(frame), index=frame.index)
    for field in ['Descrição', 'Descrição extrato', 'Descrição interno']:
        if field in frame.columns:
            part = frame[field].astype(str).str.lower().str.contains(clean, na=False)
            mask = mask | part
    return frame[mask]
