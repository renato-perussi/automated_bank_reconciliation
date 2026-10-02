'''Temp file persistence and raw loading.'''

import tempfile
from decimal import InvalidOperation
from pathlib import Path
from zipfile import BadZipFile

import pandas as pd
import streamlit as st
from openpyxl.utils.exceptions import InvalidFileException

from src.loader import load_table, validate_not_empty
from src.logger import get_logger

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
    except (OSError, RuntimeError, KeyError, InvalidOperation) as exc:
        logger.warning(f'Load failed with {exc}')
        st.error('Não foi possível ler o arquivo. Verifique o formato.')
        return None
    except (BadZipFile, InvalidFileException) as exc:
        logger.warning(f'Load failed with {exc}')
        st.error('Não foi possível ler o arquivo. Verifique o formato.')
        return None
    finally:
        try:
            temp_path.unlink(missing_ok=True)
        except OSError as exc:
            logger.warning(f'Cleanup failed with {exc}')
