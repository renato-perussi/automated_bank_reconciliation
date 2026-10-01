'''Deterministic workbook bytes without timestamps.'''

import io
from datetime import datetime
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

from openpyxl import Workbook
from openpyxl.writer.excel import ExcelWriter

from src.config import APP_VERSION


def _new_deterministic_workbook() -> Workbook:
    '''Create workbook with fixed properties for idempotent bytes.'''
    book = Workbook()
    fixed = datetime(2026, 1, 1, 0, 0, 0)
    book.properties.created = fixed
    book.properties.modified = fixed
    book.properties.creator = 'automated_bank_reconciliation'
    book.properties.lastModifiedBy = f'automated_bank_reconciliation {APP_VERSION}'
    return book


def _fixed_zip_stamp() -> tuple:
    '''Return fixed zip date tuple for deterministic bytes.'''
    return (2026, 1, 1, 0, 0, 0)


def _repack_fixed_date(payload: bytes) -> bytes:
    '''Repack zip entries with fixed date for idempotency.'''
    stamp = _fixed_zip_stamp()
    source = ZipFile(io.BytesIO(payload), 'r')
    target = io.BytesIO()
    with ZipFile(target, 'w', ZIP_DEFLATED, allowZip64=True) as dest:
        for info in source.infolist():
            data = source.read(info.filename)
            fresh = ZipInfo(info.filename, date_time=stamp)
            fresh.compress_type = info.compress_type
            fresh.external_attr = info.external_attr
            dest.writestr(fresh, data)
    source.close()
    return target.getvalue()


def _save_deterministic_bytes(book: Workbook) -> bytes:
    '''Save workbook bypassing timestamp overwrite for idempotency.'''
    fixed = datetime(2026, 1, 1, 0, 0, 0)
    book.properties.created = fixed
    book.properties.modified = fixed
    buffer = io.BytesIO()
    archive = ZipFile(buffer, 'w', ZIP_DEFLATED, allowZip64=True)
    writer = ExcelWriter(book, archive)
    writer.save()
    return _repack_fixed_date(buffer.getvalue())
