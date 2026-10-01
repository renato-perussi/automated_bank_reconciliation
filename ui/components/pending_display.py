'''Pending side display tables.'''

import pandas as pd

from src.labels import reason_label as _shared_reason_label
from ui.components.base import _display_amount, _display_date, _display_text, _lookup_field


def build_pending_side(
    pending_frame: pd.DataFrame, source_frame: pd.DataFrame, side: str
) -> pd.DataFrame:
    '''Build unmatched side table with pt-BR columns.'''
    columns = ['Data', 'Descrição', 'Valor', 'Motivo', 'Regra']
    if pending_frame is None or len(pending_frame) == 0:
        return pd.DataFrame(columns=columns)
    subset = pending_frame[pending_frame['source'] == side]
    if len(subset) == 0:
        return pd.DataFrame(columns=columns)
    rows = [_build_pending_row(item, source_frame) for _, item in subset.iterrows()]
    return pd.DataFrame(rows, columns=columns)


def _build_pending_row(item: pd.Series, source_frame: pd.DataFrame) -> dict:
    '''Build single pending row from statement or ledger side.'''
    side = item.get('source')
    if side == 'statement':
        idx = item.get('statement_idx')
    else:
        idx = item.get('ledger_idx')
    raw_date = _lookup_field(source_frame, idx, ['Data', 'event_date', 'normalized_date'])
    raw_desc = _lookup_field(
        source_frame, idx, ['Descrição', 'description', 'normalized_description']
    )
    raw_amount = _lookup_field(
        source_frame, idx, ['Valor', 'amount', 'normalized_value', 'normalized_amount']
    )
    return {
        'Data': _display_date(raw_date),
        'Descrição': _display_text(raw_desc),
        'Valor': _display_amount(raw_amount),
        'Motivo': _shared_reason_label(item.get('reason')),
        'Regra': item.get('rule_id'),
    }
