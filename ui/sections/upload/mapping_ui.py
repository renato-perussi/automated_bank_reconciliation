'''Column mapping selection and normalization.'''

import pandas as pd
import streamlit as st

from src.logger import get_logger
from src.mapping import apply_mapping, auto_map_columns, get_mapping_options
from src.normalize import normalize_table
from src.validate import collect_errors

logger = get_logger(__name__)


def _default_index(options: list, wished: object) -> int:
    '''Resolve default option position safely.'''
    try:
        return options.index(str(wished))
    except (ValueError, TypeError):
        return 0


def _mapping_complete(raw_frame: pd.DataFrame) -> bool:
    '''Check auto mapping found all columns.'''
    auto_map = auto_map_columns(raw_frame)
    return all(auto_map.get(key) is not None for key in ('data', 'descricao', 'valor'))


def choose_mapping(raw_frame: pd.DataFrame, prefix: str) -> dict:
    '''Collect column choices inside collapsible mapper.'''
    options = get_mapping_options(raw_frame)
    auto_map = auto_map_columns(raw_frame)
    date_default = _default_index(options, auto_map.get('data'))
    desc_default = _default_index(options, auto_map.get('descricao'))
    value_default = _default_index(options, auto_map.get('valor'))
    collapsed = _mapping_complete(raw_frame)
    label = 'Mapear colunas (auto detectado)' if collapsed else 'Mapear colunas'
    box = st.expander(label, expanded=not collapsed, icon=':material/tune:')
    with box:
        date_choice = st.selectbox('Data', options, index=date_default, key=f'{prefix}_date')
        desc_choice = st.selectbox(
            'Descrição', options, index=desc_default, key=f'{prefix}_desc'
        )
        value_choice = st.selectbox('Valor', options, index=value_default, key=f'{prefix}_value')
        return {'data': date_choice, 'descricao': desc_choice, 'valor': value_choice}


def finalize_source(raw_frame: pd.DataFrame, mapping: dict, source: str) -> tuple:
    '''Normalize mapped table splitting valid and errors.'''
    try:
        mapped = apply_mapping(raw_frame, mapping)
        normalized = normalize_table(mapped, source)
        valid, errors = collect_errors(normalized)
        return valid, errors
    except ValueError as exc:
        st.error(str(exc))
        empty = raw_frame.iloc[0:0].copy()
        return empty, pd.DataFrame(columns=['Linha', 'Motivo', 'Orientação'])
    except (RuntimeError, KeyError) as exc:
        logger.warning(f'Normalize failed with {exc}')
        st.error('Não foi possível processar as colunas. Confira o mapeamento.')
        empty = raw_frame.iloc[0:0].copy()
        return empty, pd.DataFrame(columns=['Linha', 'Motivo', 'Orientação'])
