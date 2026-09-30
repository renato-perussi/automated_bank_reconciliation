'''Error frame normalization for reports.'''

import pandas as pd

from src.reporting.headers import _ERROR_HEADERS_PT


def _normalize_error_frames(error_frames: object) -> pd.DataFrame:
    '''Consolidate error inputs into pt-BR display frame.'''
    if error_frames is None:
        return pd.DataFrame(columns=list(_ERROR_HEADERS_PT))
    if isinstance(error_frames, dict):
        frames = list(error_frames.values())
        return _concat_error_frames(frames)
    if isinstance(error_frames, (list, tuple)):
        return _concat_error_frames(list(error_frames))
    if isinstance(error_frames, pd.DataFrame):
        return _clean_error_frame(error_frames)
    return pd.DataFrame(columns=list(_ERROR_HEADERS_PT))


def _concat_error_frames(frames: list) -> pd.DataFrame:
    '''Concat multiple error frames normalizing headers.'''
    cleaned: list = []
    for frame in frames:
        if frame is None or len(frame) == 0:
            continue
        cleaned.append(_clean_error_frame(frame))
    if not cleaned:
        return pd.DataFrame(columns=list(_ERROR_HEADERS_PT))
    merged = pd.concat(cleaned, ignore_index=True)
    return merged[list(_ERROR_HEADERS_PT)]


def _clean_error_frame(frame: pd.DataFrame) -> pd.DataFrame:
    '''Rename Orientação to Como corrigir preserving content.'''
    work = frame.copy()
    if 'Orientação' in list(work.columns) and 'Como corrigir' not in list(work.columns):
        work = work.rename(columns={'Orientação': 'Como corrigir'})
    for field in _ERROR_HEADERS_PT:
        if field not in list(work.columns):
            work[field] = ''
    return work[list(_ERROR_HEADERS_PT)]


def _error_detail_rows(error_frames: object) -> list:
    '''Convert error summaries to exception detail rows.'''
    rows: list = []
    if error_frames is None:
        return rows
    if isinstance(error_frames, dict):
        for key, frame in error_frames.items():
            origin = 'Interno' if str(key).lower().startswith('ledger') else 'Extrato'
            rows.extend(_error_frame_rows(frame, origin))
        return rows
    if isinstance(error_frames, (list, tuple)):
        for pos, frame in enumerate(error_frames):
            origin = 'Interno' if pos == 1 and len(error_frames) == 2 else 'Extrato'
            rows.extend(_error_frame_rows(frame, origin))
        return rows
    if isinstance(error_frames, pd.DataFrame):
        return _error_frame_rows(error_frames, 'Extrato')
    return rows


def _error_frame_rows(frame: object, origin: str) -> list:
    '''Build detail rows for single error frame.'''
    rows: list = []
    if frame is None or len(frame) == 0:
        return rows
    clean = _clean_error_frame(frame)
    for _, item in clean.iterrows():
        rows.append(
            {
                'Origem': origin,
                'Data original': '',
                'Data normalizada': '',
                'Descrição original': '',
                'Valor original': '',
                'Valor normalizado': None,
                'Sinal': None,
                'Status': 'Erro',
                'Par ID': '',
                'Diferença dias': None,
                'Diferença valor': None,
                'Score descrição': None,
                'Regra ID': '',
                'Motivo': str(item.get('Motivo', '')),
                'Ação manual': '',
            }
        )
    return rows
