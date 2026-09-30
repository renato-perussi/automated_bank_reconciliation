'''Exceptions csv with params header and desc order.'''

import io

import pandas as pd

from src.logger import get_logger
from src.reporting.details import _collect_all_detail
from src.reporting.errors import _error_detail_rows
from src.reporting.formatting import _sort_number
from src.reporting.headers import _REPORT_HEADERS, _manual_lookup
from src.reporting.snapshots import _infer_params, _params_snapshot

logger = get_logger(__name__)


def _exceptions_frame(
    results: dict,
    statement_df: object,
    ledger_frame: object,
    error_frames: object,
    manual: dict,
) -> pd.DataFrame:
    '''Build sorted exceptions frame excluding auto.'''
    detail = _collect_all_detail(results, statement_df, ledger_frame, manual)
    rows: list = []
    rows.extend(detail.get('potential', []))
    rows.extend(detail.get('pending', []))
    rows.extend(detail.get('divergent', []))
    rows.extend(detail.get('duplicate', []))
    rows.extend(_error_detail_rows(error_frames))
    if not rows:
        return pd.DataFrame(columns=list(_REPORT_HEADERS))
    frame = pd.DataFrame(rows, columns=list(_REPORT_HEADERS))
    frame['_sort_key'] = frame['Valor normalizado'].map(_sort_number)
    frame = frame.sort_values(by='_sort_key', ascending=False, na_position='last')
    return frame.drop(columns=['_sort_key']).reset_index(drop=True)


def build_exceptions_csv(
    results: dict,
    params: object = None,
    statement_df: object = None,
    ledger_frame: object = None,
    error_frames: object = None,
    review_log: object = None,
) -> bytes:
    '''Generate csv bytes with only exceptions ordered desc.'''
    snapshot = _params_snapshot(params if isinstance(params, dict) else _infer_params(results))
    manual = _manual_lookup(review_log)
    frame = _exceptions_frame(results, statement_df, ledger_frame, error_frames, manual)
    buffer = io.StringIO()
    day = snapshot.get('date_tolerance_days')
    fuzzy = snapshot.get('fuzzy_threshold')
    tolerance = snapshot.get('value_tolerance')
    version = snapshot.get('APP_VERSION', snapshot.get('app_version'))
    buffer.write(f'# date_tolerance_days={day}\n')
    buffer.write(f'# fuzzy_threshold={fuzzy}\n')
    buffer.write(f'# value_tolerance={tolerance}\n')
    buffer.write(f'# APP_VERSION={version}\n')
    frame.to_csv(buffer, index=False)
    logger.info('Built exceptions csv with snapshot version.')
    return buffer.getvalue().encode('utf-8')
