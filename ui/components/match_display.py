'''Matched pair display tables.'''

import pandas as pd

from src.labels import reason_label as _shared_reason_label
from ui.components.base import (
    _display_amount,
    _display_date,
    _display_text,
    _lookup_field,
    format_brl,
)


def build_match_display(
    match_frame: pd.DataFrame,
    statement_frame: pd.DataFrame,
    ledger_frame: pd.DataFrame,
    manual_ids: set | None = None,
) -> pd.DataFrame:
    '''Enrich matched pairs with original pt-BR columns.'''
    columns = [
        'Par ID',
        'Data extrato',
        'Descrição extrato',
        'Valor extrato',
        'Data interno',
        'Descrição interno',
        'Valor interno',
        'Diferença dias',
        'Diferença valor',
        'Similaridade',
        'Regra',
        'Motivo',
        'Ação manual',
    ]
    marked = manual_ids if isinstance(manual_ids, set) else set()
    if match_frame is None or len(match_frame) == 0:
        return pd.DataFrame(columns=columns)
    rows = [
        _build_single_row(item, statement_frame, ledger_frame, marked)
        for _, item in match_frame.iterrows()
    ]
    return pd.DataFrame(rows, columns=columns)


def _side_triple(source: pd.DataFrame, idx: object) -> tuple:
    '''Extract date description amount triple for index.'''
    date_val = _lookup_field(source, idx, ['Data', 'event_date', 'normalized_date'])
    desc_val = _lookup_field(source, idx, ['Descrição', 'description', 'normalized_description'])
    amount_val = _lookup_field(
        source, idx, ['Valor', 'amount', 'normalized_value', 'normalized_amount']
    )
    return (date_val, desc_val, amount_val)


def _build_single_row(
    item: pd.Series, statement_frame: pd.DataFrame, ledger_frame: pd.DataFrame, marked: set
) -> dict:
    '''Build single enriched row with translated audit fields.'''
    first = item.get('statement_idx')
    second = item.get('ledger_idx')
    pair = item.get('match_id')
    manual = 'Confirmada manualmente' if pair in marked else ''
    statement_vals = _side_triple(statement_frame, first)
    ledger_vals = _side_triple(ledger_frame, second)
    return {
        'Par ID': pair if pair is not None else '—',
        'Data extrato': _display_date(statement_vals[0]),
        'Descrição extrato': _display_text(statement_vals[1]),
        'Valor extrato': _display_amount(statement_vals[2]),
        'Data interno': _display_date(ledger_vals[0]),
        'Descrição interno': _display_text(ledger_vals[1]),
        'Valor interno': _display_amount(ledger_vals[2]),
        'Diferença dias': item.get('day_diff'),
        'Diferença valor': format_brl(item.get('value_diff')),
        'Similaridade': item.get('description_score'),
        'Regra': item.get('rule_id'),
        'Motivo': _shared_reason_label(item.get('reason')),
        'Ação manual': manual,
    }


def build_comparison_frame(detail: pd.Series) -> pd.DataFrame:
    '''Build extrato versus interno field table.'''
    columns = ['Campo', 'Extrato', 'Interno']
    date_row = {
        'Campo': 'Data',
        'Extrato': _display_date(detail.get('Data extrato')),
        'Interno': _display_date(detail.get('Data interno')),
    }
    desc_row = {
        'Campo': 'Descrição',
        'Extrato': _display_text(detail.get('Descrição extrato')),
        'Interno': _display_text(detail.get('Descrição interno')),
    }
    amount_row = {
        'Campo': 'Valor',
        'Extrato': _display_amount(detail.get('Valor extrato')),
        'Interno': _display_amount(detail.get('Valor interno')),
    }
    return pd.DataFrame([date_row, desc_row, amount_row], columns=columns)


def build_audit_frame(detail: pd.Series) -> pd.DataFrame:
    '''Build static audit metric table for review.'''
    columns = ['Métrica', 'Valor']
    rows = [
        {'Métrica': 'Diferença dias', 'Valor': _display_text(detail.get('Diferença dias'))},
        {'Métrica': 'Diferença valor', 'Valor': _display_text(detail.get('Diferença valor'))},
        {'Métrica': 'Similaridade', 'Valor': _display_text(detail.get('Similaridade'))},
        {'Métrica': 'Regra', 'Valor': _display_text(detail.get('Regra'))},
    ]
    return pd.DataFrame(rows, columns=columns)
