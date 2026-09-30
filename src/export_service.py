'''Build export bytes without streamlit or files.'''

from src.logger import get_logger
from src.report import build_conciliation_workbook, build_exceptions_csv

logger = get_logger(__name__)


def build_export_bytes(
    results: object,
    params: object,
    statement_frame: object,
    ledger_frame: object,
    statement_errors: object,
    ledger_errors: object,
    review_log: object,
) -> tuple:
    '''Build excel csv bytes in memory without files.'''
    errors = {'statement': statement_errors, 'ledger': ledger_errors}
    try:
        excel_bytes = build_conciliation_workbook(
            results, params, statement_frame, ledger_frame, errors, review_log
        )
    except (ValueError, KeyError, RuntimeError) as exc:
        logger.warning(f'Excel build failed with {exc}')
        excel_bytes = b''
    try:
        csv_bytes = build_exceptions_csv(
            results, params, statement_frame, ledger_frame, errors, review_log
        )
    except (ValueError, KeyError, RuntimeError) as exc:
        logger.warning(f'Csv build failed with {exc}')
        csv_bytes = b''
    return excel_bytes, csv_bytes
