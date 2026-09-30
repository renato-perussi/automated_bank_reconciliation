'''Interface helpers following Apple minimal tokens.'''

from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

import pandas as pd
import streamlit as st

from src.logger import get_logger

logger = get_logger(__name__)


def load_styles() -> None:
    '''Inject shared stylesheet into streamlit page.'''
    style_path = Path(__file__).resolve().parent / 'styles.css'
    try:
        css_text = style_path.read_text(encoding='utf-8')
    except OSError as exc:
        logger.warning(f'Style load failed with {exc}')
        return
    st.markdown(f'<style>{css_text}</style>', unsafe_allow_html=True)


def render_header() -> None:
    '''Render main title and subtitle.'''
    st.markdown('<h1 class="display-lg">Conciliação Bancária</h1>', unsafe_allow_html=True)
    st.markdown(
        '<p class="body-text">Compare o extrato com os lançamentos internos em poucos passos.</p>',
        unsafe_allow_html=True,
    )


def _compact_label(label: str) -> str:
    '''Glue percent sign to first word with nbsp.'''
    return str(label).replace('% ', '% ')


def render_kpi_card(label: str, value: str) -> None:
    '''Render single indicator inside pearl card.'''
    safe_label = _compact_label(label)
    safe_value = str(value)
    st.markdown(
        f'<div class="kpi-card"><div class="kpi-label">{safe_label}</div>'
        f'<div class="kpi-value">{safe_value}</div></div>',
        unsafe_allow_html=True,
    )


def build_column_config(frame: pd.DataFrame) -> dict:
    '''Build typed config with BRL dates and pinned id.'''
    config: dict = {}
    if frame is None or len(frame) == 0:
        return config
    for field in ['Valor', 'Valor extrato', 'Valor interno', 'Diferença valor']:
        if field in list(frame.columns):
            config[field] = st.column_config.NumberColumn(format='R$ %.2f')
    for field in ['Data', 'Data extrato', 'Data interno']:
        if field in list(frame.columns):
            config[field] = st.column_config.DateColumn(format='DD/MM/YYYY')
    if 'Data/Hora' in list(frame.columns):
        fmt = 'DD/MM/YYYY HH:mm:ss'
        config['Data/Hora'] = st.column_config.DatetimeColumn(format=fmt)
    if 'Par ID' in list(frame.columns):
        config['Par ID'] = st.column_config.TextColumn(pinned=True)
    return config


def render_status_table(frame: pd.DataFrame) -> None:
    '''Render result table with empty pt-BR fallback.'''
    if frame is None or len(frame) == 0:
        st.markdown(
            '<p class="body-text">Nenhum registro encontrado.</p>', unsafe_allow_html=True
        )
        return
    st.dataframe(frame, hide_index=True, column_config=build_column_config(frame))


def format_pct(raw_value: object) -> str:
    '''Format percentage using pt-BR decimal comma.'''
    try:
        text = f'{float(raw_value):.1f}'
    except (ValueError, TypeError):
        return '—'
    return f'{text.replace(".", ",")}%'


def format_brl(raw_value: object) -> str:
    '''Format numeric input as pt-BR currency text.'''
    if raw_value is None:
        return '—'
    try:
        if pd.isna(raw_value):
            return '—'
    except (ValueError, TypeError):
        pass
    try:
        amount = Decimal(str(raw_value))
    except (InvalidOperation, ValueError, TypeError):
        return str(raw_value)
    quantized = amount.quantize(Decimal('0.00'))
    text = f'{quantized:,.2f}'
    text = text.replace(',', 'X').replace('.', ',').replace('X', '.')
    return f'R$ {text}'


def calc_kpis(results: dict, statement_count: int, ledger_count: int) -> dict:
    '''Calculate totals and percentages from result tables.'''
    auto_count = len(results.get('auto'))
    potential_count = len(results.get('potential'))
    pending_count = len(results.get('pending'))
    divergent_count = len(results.get('divergent'))
    duplicate_count = len(results.get('duplicate'))
    unified = auto_count + potential_count + pending_count + divergent_count
    unified = unified + duplicate_count
    if unified == 0:
        pct_auto = 0.0
        pct_review = 0.0
        pct_pending = 0.0
        pct_divergent = 0.0
    else:
        pct_auto = round(auto_count / unified * 100, 1)
        pct_review = round(potential_count / unified * 100, 1)
        pct_pending = round(pending_count / unified * 100, 1)
        pct_divergent = round((divergent_count + duplicate_count) / unified * 100, 1)
    exception_rate = round(100.0 - pct_auto, 1)
    return {
        'total_statement': int(statement_count),
        'total_ledger': int(ledger_count),
        'pct_auto': float(pct_auto),
        'pct_review': float(pct_review),
        'pct_pending': float(pct_pending),
        'pct_divergent': float(pct_divergent),
        'exception_rate': float(exception_rate),
    }


def _lookup_field(source: pd.DataFrame, idx: object, fields: list) -> object:
    '''Return first available field value for index.'''
    if source is None or len(source) == 0:
        return '—'
    if idx is None:
        return '—'
    try:
        if idx not in source.index:
            return '—'
        row = source.loc[idx]
    except (KeyError, ValueError, TypeError):
        return '—'
    for field in fields:
        if field in source.columns:
            try:
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
    return '—'


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
        'Score',
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
        'Data extrato': statement_vals[0],
        'Descrição extrato': statement_vals[1],
        'Valor extrato': statement_vals[2],
        'Data interno': ledger_vals[0],
        'Descrição interno': ledger_vals[1],
        'Valor interno': ledger_vals[2],
        'Diferença dias': item.get('day_diff'),
        'Diferença valor': item.get('value_diff'),
        'Score': item.get('description_score'),
        'Regra': item.get('rule_id'),
        'Motivo': item.get('reason'),
        'Ação manual': manual,
    }


def _display_text(raw: object) -> str:
    '''Format cell value with empty fallback.'''
    if raw is None:
        return '—'
    try:
        if pd.isna(raw):
            return '—'
    except (ValueError, TypeError):
        pass
    if isinstance(raw, pd.Timestamp):
        return raw.strftime('%d/%m/%Y')
    if isinstance(raw, datetime):
        return raw.strftime('%d/%m/%Y')
    if isinstance(raw, date):
        return raw.strftime('%d/%m/%Y')
    text = str(raw).strip()
    if text == '' or text == '—' or text.lower() in ('nan', 'nat', 'none'):
        return '—'
    return text


def _display_date(raw: object) -> str:
    '''Format date value as DD/MM/YYYY with fallback.'''
    text = _display_text(raw)
    if text == '—':
        return text
    try:
        return pd.to_datetime(text, format='%Y-%m-%d').strftime('%d/%m/%Y')
    except (ValueError, TypeError):
        pass
    try:
        parsed = pd.to_datetime(text, dayfirst=True, errors='coerce')
        if pd.isna(parsed):
            return text
        return parsed.strftime('%d/%m/%Y')
    except (ValueError, TypeError):
        return text


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
        'Extrato': _display_text(detail.get('Valor extrato')),
        'Interno': _display_text(detail.get('Valor interno')),
    }
    return pd.DataFrame([date_row, desc_row, amount_row], columns=columns)


def build_audit_frame(detail: pd.Series) -> pd.DataFrame:
    '''Build static audit metric table for review.'''
    columns = ['Métrica', 'Valor']
    rows = [
        {'Métrica': 'Diferença dias', 'Valor': _display_text(detail.get('Diferença dias'))},
        {'Métrica': 'Diferença valor', 'Valor': format_brl(detail.get('Diferença valor'))},
        {'Métrica': 'Score', 'Valor': _display_text(detail.get('Score'))},
        {'Métrica': 'Regra', 'Valor': _display_text(detail.get('Regra'))},
    ]
    return pd.DataFrame(rows, columns=columns)


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
    return {
        'Data': _lookup_field(source_frame, idx, ['Data', 'event_date', 'normalized_date']),
        'Descrição': _lookup_field(
            source_frame, idx, ['Descrição', 'description', 'normalized_description']
        ),
        'Valor': _lookup_field(
            source_frame, idx, ['Valor', 'amount', 'normalized_value', 'normalized_amount']
        ),
        'Motivo': item.get('reason'),
        'Regra': item.get('rule_id'),
    }
