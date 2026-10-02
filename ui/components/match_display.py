'''Matched pair display tables.'''

import pandas as pd

from src.labels import reason_label as _shared_reason_label
from ui.components.base import (
    _display_amount,
    _display_date,
    _display_text,
    format_brl,
    side_triple,
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
        frame = pd.DataFrame(columns=columns)
    else:
        rows = [
            _build_single_row(item, statement_frame, ledger_frame, marked)
            for _, item in match_frame.iterrows()
        ]
        frame = pd.DataFrame(rows, columns=columns)
    if frame.empty or not frame['Ação manual'].ne('').any():
        frame = frame.drop(columns=['Ação manual'])
    return frame


def _duplicate_source_label(source: object) -> str:
    '''Map duplicate source code to pt-BR base name.'''
    text = str(source)
    if text == 'statement':
        return 'Extrato'
    if text == 'ledger':
        return 'Interno'
    return '—'


def _build_duplicate_row(
    item: pd.Series, statement_frame: pd.DataFrame, ledger_frame: pd.DataFrame
) -> dict:
    '''Build single side row reading only the duplicated base.'''
    if str(item.get('source')) == 'statement':
        date_val, desc_val, amount_val = side_triple(statement_frame, item.get('statement_idx'))
    else:
        date_val, desc_val, amount_val = side_triple(ledger_frame, item.get('ledger_idx'))
    return {
        'Par ID': _display_text(item.get('match_id')),
        'Base': _duplicate_source_label(item.get('source')),
        'Data': _display_date(date_val),
        'Descrição': _display_text(desc_val),
        'Valor': _display_amount(amount_val),
        'Regra': _display_text(item.get('rule_id')),
        'Motivo': _shared_reason_label(item.get('reason')),
    }


def build_duplicate_display(
    dup_frame: pd.DataFrame, statement_frame: pd.DataFrame, ledger_frame: pd.DataFrame
) -> pd.DataFrame:
    '''Build single side list for intra base duplicates.'''
    columns = ['Par ID', 'Base', 'Data', 'Descrição', 'Valor', 'Regra', 'Motivo']
    if dup_frame is None or len(dup_frame) == 0:
        return pd.DataFrame(columns=columns)
    rows = [
        _build_duplicate_row(item, statement_frame, ledger_frame)
        for _, item in dup_frame.iterrows()
    ]
    return pd.DataFrame(rows, columns=columns)


def _build_single_row(
    item: pd.Series, statement_frame: pd.DataFrame, ledger_frame: pd.DataFrame, marked: set
) -> dict:
    '''Build single enriched row with translated audit fields.'''
    first = item.get('statement_idx')
    second = item.get('ledger_idx')
    pair = item.get('match_id')
    manual = 'Confirmada manualmente' if pair in marked else ''
    statement_vals = side_triple(statement_frame, first)
    ledger_vals = side_triple(ledger_frame, second)
    return {
        'Par ID': _display_text(pair),
        'Data extrato': _display_date(statement_vals[0]),
        'Descrição extrato': _display_text(statement_vals[1]),
        'Valor extrato': _display_amount(statement_vals[2]),
        'Data interno': _display_date(ledger_vals[0]),
        'Descrição interno': _display_text(ledger_vals[1]),
        'Valor interno': _display_amount(ledger_vals[2]),
        'Diferença dias': item.get('day_diff'),
        'Diferença valor': format_brl(item.get('value_diff')),
        'Similaridade': item.get('description_score'),
        'Regra': _display_text(item.get('rule_id')),
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
