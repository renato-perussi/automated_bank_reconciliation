'''Mapping of pt-BR headers to internal english fields.'''

import re
import unicodedata

import pandas as pd

from src.logger import get_logger

logger = get_logger(__name__)

_INTERNAL_FIELDS = {'data': 'event_date', 'descricao': 'description', 'valor': 'amount'}

_DISPLAY_FIELDS = {'data': 'Data', 'descricao': 'Descrição', 'valor': 'Valor'}

_DATA_KEYS = {'data', 'date', 'dt', 'data_lancamento'}

_DESC_KEYS = {'descricao', 'historico', 'description', 'memo'}

_VALUE_KEYS = {'valor', 'value', 'amount', 'montante'}


def normalize_header(name: object) -> str:
    '''Normalize header removing accent case spaces punctuation.'''
    if name is None:
        return ''
    text = str(name).strip().lower()
    folded = unicodedata.normalize('NFKD', text)
    stripped = ''.join([c for c in folded if not unicodedata.combining(c)])
    underscored = re.sub(r'[\s\-]+', '_', stripped)
    cleaned = re.sub(r'[^a-z0-9_]', '', underscored)
    collapsed = re.sub(r'_+', '_', cleaned).strip('_')
    return collapsed


def auto_map_columns(frame: pd.DataFrame) -> dict:
    '''Auto detect logical columns from original header.'''
    found: dict = {'data': None, 'descricao': None, 'valor': None}
    seen: dict = {}
    for item in list(frame.columns):
        key = normalize_header(item)
        if key not in seen:
            seen[key] = item
    for key, item in seen.items():
        if key in _DATA_KEYS and found['data'] is None:
            found['data'] = item
        elif key in _DESC_KEYS and found['descricao'] is None:
            found['descricao'] = item
        elif key in _VALUE_KEYS and found['valor'] is None:
            found['valor'] = item
    logger.info(f'Mapped columns to {found}')
    return found


def apply_mapping(frame: pd.DataFrame, mapping: dict) -> pd.DataFrame:
    '''Map original columns to internal fields preserving originals.'''
    for logical in ('data', 'descricao', 'valor'):
        chosen = mapping.get(logical) if isinstance(mapping, dict) else None
        if chosen is None or chosen not in list(frame.columns):
            label = _DISPLAY_FIELDS[logical]
            raise ValueError(
                f'Coluna obrigatória não encontrada: {label}. Mapeie manualmente.'
            )
    result = frame.copy()
    for logical, field in _INTERNAL_FIELDS.items():
        result[field] = result[mapping[logical]]
    return result


def get_mapping_options(frame: pd.DataFrame) -> list:
    '''Expose original columns for interface selection.'''
    return [str(item) for item in list(frame.columns)]
