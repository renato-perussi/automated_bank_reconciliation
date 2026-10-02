'''Preview display and error badges.'''

import pandas as pd
import streamlit as st

from src.display import to_amount_text, to_date_text, to_text
from src.loader import get_preview
from src.report import _clean_error_frame
from ui.components import build_column_config


def format_error_display(frame: pd.DataFrame) -> pd.DataFrame:
    '''Translate Orientação to Como corrigir for display.'''
    if frame is None or len(frame) == 0:
        return pd.DataFrame(columns=['Linha', 'Motivo', 'Como corrigir'])
    return _clean_error_frame(frame)


def _render_source_status(valid: pd.DataFrame, errors: pd.DataFrame) -> None:
    '''Show valid error badges after mapping.'''
    total_valid = 0 if valid is None else len(valid)
    total_errors = 0 if errors is None else len(errors)
    st.badge(f'{total_valid} linhas válidas', icon=':material/check:', color='green')
    if total_errors == 0:
        return
    st.badge(f'{total_errors} linhas com erro', icon=':material/warning:', color='orange')


def _build_preview_display(raw_frame: pd.DataFrame, mapping: dict) -> pd.DataFrame:
    '''Build pt-BR preview with display names and formats.'''
    if raw_frame is None:
        return pd.DataFrame()
    preview = get_preview(raw_frame, 5)
    if not isinstance(mapping, dict):
        return preview
    try:
        date_col = mapping.get('data')
        desc_col = mapping.get('descricao')
        value_col = mapping.get('valor')
        names = list(preview.columns)
        if date_col not in names or desc_col not in names or value_col not in names:
            return preview
        return pd.DataFrame(
            {
                'Data': preview[date_col].map(to_date_text),
                'Descrição': preview[desc_col].map(to_text),
                'Valor': preview[value_col].map(to_amount_text),
            }
        )
    except (KeyError, ValueError, TypeError, AttributeError):
        return preview


def show_preview_errors(
    raw_frame: pd.DataFrame, error_frame: pd.DataFrame, prefix: str, title: str, mapping: dict
) -> None:
    '''Show preview plus pt-BR error table.'''
    has_errors = error_frame is not None and len(error_frame) > 0
    total_errors = 0 if error_frame is None else len(error_frame)
    shown = min(5, len(raw_frame)) if raw_frame is not None else 0
    if has_errors:
        label = f'{title} ({total_errors} erros)'
        icon = ':material/warning:'
    else:
        label = f'{title} ({shown} linhas)'
        icon = ':material/preview:'
    box = st.expander(
        label, expanded=has_errors, icon=icon, on_change='rerun', key=f'{prefix}_preview'
    )
    if box.open is False:
        return
    with box:
        display = _build_preview_display(raw_frame, mapping)
        st.dataframe(display, hide_index=True, column_config=build_column_config(display))
        if has_errors:
            st.markdown('<p class="body-text">Erros encontrados</p>', unsafe_allow_html=True)
            errors = format_error_display(error_frame)
            st.dataframe(errors, hide_index=True, column_config=build_column_config(errors))
        else:
            st.caption('Sem erros.')
