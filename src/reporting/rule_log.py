'''Auditable rule log builders.'''

import pandas as pd

from src.reporting.errors import _normalize_error_frames
from src.reporting.headers import _manual_lookup
from src.reporting.snapshots import _infer_params, _params_snapshot


def build_rule_log(
    results: dict, review_log: object = None, error_frames: object = None
) -> pd.DataFrame:
    '''Build auditable log with rule manual and error fields.'''
    manual = _manual_lookup(review_log)
    snapshot = _params_snapshot(_infer_params(results))
    rows = _collect_match_log_rows(results, manual)
    rows.extend(_collect_error_log_rows(error_frames, snapshot, manual))
    columns = [
        'match_id',
        'rule_id',
        'day_diff',
        'value_diff',
        'description_score',
        'reason',
        'error_code',
        'review_action',
        'timestamp',
        'params_snapshot',
    ]
    if not rows:
        return pd.DataFrame(columns=columns)
    return pd.DataFrame(rows, columns=columns)


def _collect_match_log_rows(results: dict, manual: dict) -> list:
    '''Collect log rows for five result tables.'''
    rows: list = []
    if not isinstance(results, dict):
        return rows
    for key in ('auto', 'potential', 'pending', 'divergent', 'duplicate'):
        frame = results.get(key)
        if frame is None or len(frame) == 0:
            continue
        for _, item in frame.iterrows():
            rows.append(_match_log_row(item, manual))
    return rows


def _match_log_row(item: object, manual: dict) -> dict:
    '''Build single log row with manual overlay.'''
    pair = item.get('match_id')
    entry = manual.get(str(pair), {}) if pair is not None else {}
    snapshot = item.get('params_snapshot')
    clean_snapshot = dict(snapshot) if isinstance(snapshot, dict) else {}
    return {
        'match_id': pair,
        'rule_id': item.get('rule_id'),
        'day_diff': item.get('day_diff'),
        'value_diff': item.get('value_diff'),
        'description_score': item.get('description_score'),
        'reason': item.get('reason'),
        'error_code': '',
        'review_action': entry.get('review_action', ''),
        'timestamp': entry.get('timestamp', ''),
        'params_snapshot': clean_snapshot,
    }


def _collect_error_log_rows(error_frames: object, snapshot: dict, manual: dict) -> list:
    '''Collect log rows for validation errors.'''
    rows: list = []
    display = _normalize_error_frames(error_frames)
    if len(display) == 0:
        return rows
    for _, item in display.iterrows():
        rows.append(_error_log_row(item, snapshot))
    return rows


def _error_log_row(item: object, snapshot: dict) -> dict:
    '''Build log row inferring error code from motive.'''
    motive = str(item.get('Motivo', ''))
    code = _infer_error_code(motive)
    return {
        'match_id': None,
        'rule_id': 'RN-09',
        'day_diff': None,
        'value_diff': None,
        'description_score': None,
        'reason': motive,
        'error_code': code,
        'review_action': '',
        'timestamp': '',
        'params_snapshot': dict(snapshot),
    }


def _infer_error_code(motive: str) -> str:
    '''Infer machine code from pt-BR motive text.'''
    text = str(motive).lower()
    if 'data inválida' in text or 'data invalida' in text:
        return 'DATA_INVALIDA'
    if 'valor inválido' in text or 'valor invalido' in text:
        return 'VALOR_INVALIDO'
    if 'coluna obrigatória' in text or 'coluna obrigatoria' in text:
        return 'COLUNA_AUSENTE'
    return 'ERRO_VALIDACAO'
