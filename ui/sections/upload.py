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


def choose_mapping(raw_frame: pd.DataFrame, prefix: str) -> dict:
    '''Collect column choices with auto mapped defaults.'''
    options = get_mapping_options(raw_frame)
    auto_map = auto_map_columns(raw_frame)
    date_default = _default_index(options, auto_map.get('data'))
    desc_default = _default_index(options, auto_map.get('descricao'))
    value_default = _default_index(options, auto_map.get('valor'))
    date_choice = st.selectbox('Data', options, index=date_default, key=f'{prefix}_date')
    desc_choice = st.selectbox('Descrição', options, index=desc_default, key=f'{prefix}_desc')
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


def show_preview_errors(
    raw_frame: pd.DataFrame, error_frame: pd.DataFrame, prefix: str
) -> None:
    '''Show five row preview plus pt-BR error table.'''
    box = st.expander(
        'Prévia e erros', expanded=False, icon=':material/preview:', on_change='rerun',
        key=f'{prefix}_preview',
    )
    if box.open is False:
        return
    with box:
        st.markdown('<p class="body-text">Prévia (5 linhas)</p>', unsafe_allow_html=True)
        st.dataframe(get_preview(raw_frame, 5), hide_index=True)
        if error_frame is not None and len(error_frame) > 0:
            st.markdown('<p class="body-text">Erros encontrados</p>', unsafe_allow_html=True)
            display = format_error_display(error_frame)
            st.dataframe(display, hide_index=True, column_config=build_column_config(display))


def render_single_upload(
    uploader_label: str, source: str, frame_key: str, error_key: str, prefix: str
) -> None:
    '''Render one uploader with mapping preview errors.'''
    uploaded = st.file_uploader(uploader_label, type=['csv', 'xls', 'xlsx'], key=f'{prefix}_up')
    st.markdown(
        '<p class="upload-note">Limite 20 MB por arquivo • CSV ou Excel</p>',
        unsafe_allow_html=True,
    )
    if uploaded is None:
        return
    raw_frame = fetch_raw_table(uploaded)
    if raw_frame is None:
        return
    mapping = choose_mapping(raw_frame, prefix)
    valid, errors = finalize_source(raw_frame, mapping, source)
    st.session_state[frame_key] = valid
    st.session_state[error_key] = errors
    show_preview_errors(raw_frame, errors, prefix)


def render_upload_section() -> None:
    '''Render title plus two upload cards side by side.'''
    st.markdown('<h2 class="display-md">Upload dos arquivos</h2>', unsafe_allow_html=True)
    st.markdown(
        '<p class="body-text">Envie o extrato e os lançamentos internos em CSV ou Excel.</p>',
        unsafe_allow_html=True,
    )
    left_upload, right_upload = st.columns(2, gap='medium')
    with left_upload:
        with st.container(border=True):
            render_single_upload(
                'Extrato bancário (CSV ou Excel)',
                'statement',
                'statement_df',
                'statement_errors',
                'statement',
            )
    with right_upload:
        with st.container(border=True):
            render_single_upload(
                'Lançamentos internos (CSV ou Excel)',
                'ledger',
                'ledger_df',
                'ledger_errors',
                'ledger',
            )
