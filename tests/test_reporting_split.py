'''Reporting split parity checks.'''

import io

import openpyxl
import pandas as pd

import src.mapping as mapping
from src.classifier import build_result_tables
from src.loader import load_table
from src.matcher import build_params
from src.normalize import normalize_table
from src.report import build_conciliation_workbook as facade_workbook
from src.report import build_exceptions_csv as facade_csv
from src.reporting.exceptions import build_exceptions_csv as split_csv
from src.reporting.workbook import build_conciliation_workbook as split_workbook
from src.validate import collect_errors


def _load_valid() -> tuple:
    '''Load example fixtures into valid frames.'''
    raw_statement, _ = load_table('data/examples/extrato.csv')
    mapped_statement = mapping.apply_mapping(raw_statement, mapping.auto_map_columns(raw_statement))
    statement = normalize_table(mapped_statement, 'statement')
    raw_ledger, _ = load_table('data/examples/interno.xlsx')
    mapped_ledger = mapping.apply_mapping(raw_ledger, mapping.auto_map_columns(raw_ledger))
    ledger = normalize_table(mapped_ledger, 'ledger')
    valid_statement, errors_statement = collect_errors(statement)
    valid_ledger, errors_ledger = collect_errors(ledger)
    return valid_statement, valid_ledger, errors_statement, errors_ledger


def test_workbook_bytes_identical() -> None:
    '''Facade and split workbook produce identical bytes.'''
    valid_statement, valid_ledger, errors_statement, errors_ledger = _load_valid()
    params = build_params()
    tables = build_result_tables(valid_statement, valid_ledger, params)
    errors = {'statement': errors_statement, 'ledger': errors_ledger}
    first = facade_workbook(tables, params, valid_statement, valid_ledger, errors)
    second = split_workbook(tables, params, valid_statement, valid_ledger, errors)
    assert first == second
    book = openpyxl.load_workbook(io.BytesIO(first))
    assert set(book.sheetnames) == {
        'Resumo',
        'Conciliadas',
        'Para_Revisao',
        'Pendentes',
        'Divergentes',
        'Duplicadas',
        'Erros',
        'Log_Regras',
    }


def test_csv_bytes_identical_and_ordered() -> None:
    '''Facade and split csv identical and ordered desc.'''
    valid_statement, valid_ledger, errors_statement, errors_ledger = _load_valid()
    params = build_params()
    tables = build_result_tables(valid_statement, valid_ledger, params)
    errors = {'statement': errors_statement, 'ledger': errors_ledger}
    first = facade_csv(tables, params, valid_statement, valid_ledger, errors)
    second = split_csv(tables, params, valid_statement, valid_ledger, errors)
    assert first == second
    text = first.decode('utf-8')
    assert '# date_tolerance_days' in text
    assert '# fuzzy_threshold' in text
    assert '# value_tolerance' in text
    assert '# APP_VERSION' in text
    frame = pd.read_csv(io.BytesIO(first), comment='#')
    assert 'Conciliada' not in set(frame['Status'].tolist())
    values = pd.to_numeric(frame['Valor normalizado'], errors='coerce').tolist()
    present = [item for item in values if pd.notna(item)]
    assert present == sorted(present, reverse=True)
