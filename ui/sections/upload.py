'''Upload cards with mapping preview errors.'''

import tempfile
from pathlib import Path

import pandas as pd
import streamlit as st

from src.loader import get_preview, load_table, validate_not_empty
from src.logger import get_logger
from src.mapping import apply_mapping, auto_map_columns, get_mapping_options
from src.normalize import normalize_table
from src.report import _clean_error_frame
from src.validate import collect_errors
from ui.components import build_column_config

logger = get_logger(__name__)


def save_temp_file(uploaded_file: object) -> Path | None:
    '''Persist upload preserving suffix for loader.'''
    try:
        raw_name = str(getattr(uploaded_file, 'name', 'upload.csv'))
        suffix = Path(raw_name).suffix.lower()
        if suffix == '':
            suffix = '.csv'
        payload = uploaded_file.getbuffer()
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
        tmp.write(bytes(payload))
        tmp.close()
        return Path(tmp.name)
    except (OSError, ValueError, AttributeError) as exc:
        logger.warning(f'Temp save failed with {exc}')
        st.error('Não foi possível salvar o arquivo. Tente novamente.')
        return None


def fetch_raw_table(uploaded_file: object) -> pd.DataFrame | None:
    '''Load raw table from upload with pt-BR feedback.'''
    temp_path = save_temp_file(uploaded_file)
    if temp_path is None:
        return None
    try:
        frame, _ = load_table(temp_path)
        validate_not_empty(frame)
        return frame
    except ValueError as exc:
        st.error(str(exc))
        return None
    except (OSError, RuntimeError) as exc:
        logger.warning(f'Load failed with {exc}')
        st.error('Não foi possível ler o arquivo. Verifique o formato.')
        return None
    finally:
        try:
            temp_path.unlink(missing_ok=True)
        except OSError as exc:
            logger.warning(f'Cleanup failed with {exc}')


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


def show_preview_errors(
    raw_frame: pd.DataFrame, error_frame: pd.DataFrame, prefix: str, title: str
) -> None:
    '''Show five row preview plus pt-BR error table.'''
    has_errors = error_frame is not None and len(error_frame) > 0
    total_errors = 0 if error_frame is None else len(error_frame)
    if has_errors:
        label = f'{title} ({total_errors} erros)'
        icon = ':material/warning:'
    else:
        label = f'{title} (5 linhas)'
        icon = ':material/preview:'
    box = st.expander(
        label, expanded=has_errors, icon=icon, on_change='rerun', key=f'{prefix}_preview'
    )
    if box.open is False:
        return
    with box:
        st.markdown('<p class="body-text">Prévia (5 linhas)</p>', unsafe_allow_html=True)
        st.dataframe(get_preview(raw_frame, 5), hide_index=True)
        if has_errors:
            st.markdown('<p class="body-text">Erros encontrados</p>', unsafe_allow_html=True)
            display = format_error_display(error_frame)
            st.dataframe(display, hide_index=True, column_config=build_column_config(display))
        else:
            st.caption('Sem erros.')


def render_single_upload(
    uploader_label: str, source: str, frame_key: str, error_key: str, prefix: str
) -> tuple:
    '''Render one uploader with mapping and status.'''
    uploaded = st.file_uploader(uploader_label, type=['csv', 'xls', 'xlsx'], key=f'{prefix}_up')
    if uploaded is None:
        st.session_state[frame_key] = None
        st.session_state[error_key] = pd.DataFrame()
        return None, None, None
    raw_frame = fetch_raw_table(uploaded)
    if raw_frame is None:
        st.session_state[frame_key] = None
        st.session_state[error_key] = pd.DataFrame()
        return None, None, None
    mapping = choose_mapping(raw_frame, prefix)
    valid, errors = finalize_source(raw_frame, mapping, source)
    st.session_state[frame_key] = valid
    st.session_state[error_key] = errors
    _render_source_status(valid, errors)
    return raw_frame, valid, errors


def render_upload_section() -> None:
    '''Render title plus two upload cards side by side.'''
    st.markdown('<h2 class="display-md">1. Upload dos arquivos</h2>', unsafe_allow_html=True)
    st.markdown(
        '<p class="body-text">Selecione os dois arquivos. Nada sai deste computador.</p>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<p class="upload-note">CSV ou Excel, até 20 MB por arquivo</p>',
        unsafe_allow_html=True,
    )
    left_upload, right_upload = st.columns(2, gap='medium')
    with left_upload:
        with st.container(border=True):
            left_raw, _, left_errors = render_single_upload(
                'Extrato bancário', 'statement', 'statement_df', 'statement_errors', 'statement'
            )
    with right_upload:
        with st.container(border=True):
            right_raw, _, right_errors = render_single_upload(
                'Lançamentos internos', 'ledger', 'ledger_df', 'ledger_errors', 'ledger'
            )
    if left_raw is not None:
        show_preview_errors(left_raw, left_errors, 'statement', 'Prévia do extrato')
    if right_raw is not None:
        show_preview_errors(right_raw, right_errors, 'ledger', 'Prévia dos lançamentos')
