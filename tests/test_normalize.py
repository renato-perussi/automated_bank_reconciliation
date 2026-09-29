'''Normalization and validation checks.'''

import datetime
from decimal import Decimal
from pathlib import Path

import pandas as pd

import src.mapping as mapping
from src.loader import load_table
from src.normalize import (
    detect_sign,
    normalize_amount,
    normalize_date,
    normalize_description,
    normalize_table,
)
from src.validate import collect_errors


def test_normalize_date_ddmmyyyy() -> None:
    '''Parse brazilian date format.'''
    value, error = normalize_date('10/09/2026')
    assert value == datetime.date(2026, 9, 10)
    assert error is None


def test_normalize_date_iso() -> None:
    '''Parse iso date format.'''
    value, error = normalize_date('2026-09-10')
    assert value == datetime.date(2026, 9, 10)
    assert error is None


def test_normalize_date_dash() -> None:
    '''Parse dash brazilian date format.'''
    value, error = normalize_date('10-09-2026')
    assert value == datetime.date(2026, 9, 10)
    assert error is None


def test_normalize_date_excel_types() -> None:
    '''Parse datetime date and timestamp objects.'''
    moment = datetime.datetime(2026, 9, 10, 14, 30)
    value, error = normalize_date(moment)
    assert value == datetime.date(2026, 9, 10)
    assert error is None
    value, error = normalize_date(datetime.date(2026, 9, 10))
    assert value == datetime.date(2026, 9, 10)
    assert error is None
    value, error = normalize_date(pd.Timestamp('2026-09-10'))
    assert value == datetime.date(2026, 9, 10)
    assert error is None


def test_normalize_date_invalid() -> None:
    '''Reject invalid dates with invalid code.'''
    value, error = normalize_date('31/02/2026')
    assert value is None
    assert error == 'DATA_INVALIDA'
    value, error = normalize_date('invalida')
    assert value is None
    assert error == 'DATA_INVALIDA'
    value, error = normalize_date(None)
    assert value is None
    assert error == 'DATA_INVALIDA'
    value, error = normalize_date('')
    assert value is None
    assert error == 'DATA_INVALIDA'


def test_normalize_amount_brazilian() -> None:
    '''Parse brazilian currency with thousand and decimal marks.'''
    value, error = normalize_amount('-R$ 2.500,00')
    assert value == Decimal('-2500')
    assert error is None
    value, error = normalize_amount('R$ 4.800,00')
    assert value == Decimal('4800')
    assert error is None


def test_normalize_amount_plain_and_negative() -> None:
    '''Parse plain dot decimal and explicit negative.'''
    value, error = normalize_amount('2500.00')
    assert value == Decimal('2500.00')
    assert error is None
    value, error = normalize_amount('-2500')
    assert value == Decimal('-2500')
    assert error is None
    value, error = normalize_amount(4800)
    assert value == Decimal('4800')
    assert error is None


def test_normalize_amount_parentheses() -> None:
    '''Parentheses always mean debit.'''
    value, error = normalize_amount('(2500)')
    assert value == Decimal('-2500')
    assert error is None


def test_normalize_amount_debit_credit_suffix() -> None:
    '''Suffix markers define debit and credit.'''
    value, error = normalize_amount('2.500 D')
    assert value == Decimal('-2500')
    assert error is None
    value, error = normalize_amount('2.500 C')
    assert value == Decimal('2500')
    assert error is None


def test_normalize_amount_invalid() -> None:
    '''Reject empty and non numeric amounts.'''
    value, error = normalize_amount(None)
    assert value is None
    assert error == 'VALOR_INVALIDO'
    value, error = normalize_amount('')
    assert value is None
    assert error == 'VALOR_INVALIDO'
    value, error = normalize_amount('abc')
    assert value is None
    assert error == 'VALOR_INVALIDO'


def test_detect_sign_cases() -> None:
    '''Detect debit credit and zero precedence.'''
    assert detect_sign(Decimal('-2500'), '-R$ 2.500,00') == -1
    assert detect_sign(Decimal('4800'), 'R$ 4.800,00') == 1
    assert detect_sign(Decimal('0'), '0') == 1
    assert detect_sign(None, '(2500)') == -1
    assert detect_sign(None, '2.500 D') == -1
    assert detect_sign(None, '2.500 C') == 1
    assert detect_sign(None, '-2500') == -1
    assert detect_sign(None, '+2500') == 1


def test_normalize_description_canonical() -> None:
    '''Canonical form lowercases removes accent and punctuation.'''
    assert normalize_description('Pagamento Fornecedor X') == 'pagamento fornecedor x'
    assert normalize_description('Fornecedor X NF 1254') == 'fornecedor x nf 1254'
    assert normalize_description('Histórico  São   Paulo!') == 'historico sao paulo'
    assert normalize_description(None) == ''
    assert normalize_description('  ') == ''


def test_normalize_table_statement(fixture_paths: dict) -> None:
    '''Statement fixture normalizes without critical errors.'''
    frame, _ = load_table(fixture_paths['statement'])
    mapped = mapping.apply_mapping(frame, mapping.auto_map_columns(frame))
    result = normalize_table(mapped, 'statement')
    assert 'normalized_date' in list(result.columns)
    assert 'normalized_amount' in list(result.columns)
    assert 'normalized_value' in list(result.columns)
    assert 'normalized_description' in list(result.columns)
    first = result.iloc[0]
    assert first['normalized_date'] == datetime.date(2026, 9, 10)
    assert first['normalized_amount'] == Decimal('-2500')
    assert first['normalized_value'] == Decimal('-2500')
    assert first['sign'] == -1
    assert first['source'] == 'statement'
    assert first['error_code'] is None
    assert first['row_hash'] is not None


def test_normalize_table_ledger(fixture_paths: dict) -> None:
    '''Ledger fixture normalizes valid rows preserving originals.'''
    frame, _ = load_table(fixture_paths['ledger'])
    mapped = mapping.apply_mapping(frame, mapping.auto_map_columns(frame))
    result = normalize_table(mapped, 'ledger')
    assert len(result) == 2
    assert result.iloc[0]['normalized_amount'] == Decimal('-2500')
    assert result.iloc[1]['normalized_amount'] == Decimal('4800')
    assert result.iloc[1]['sign'] == 1
    assert 'Data' in list(result.columns)


def test_normalize_table_matrix_formats(fixture_paths: dict) -> None:
    '''Matrix fixtures normalize parentheses iso and lowercase.'''
    base = Path(fixture_paths['matrix'])
    for name in ('valor_parenteses.csv', 'data_iso.csv', 'header_minusculo.csv'):
        frame, _ = load_table(base / name)
        mapped = mapping.apply_mapping(frame, mapping.auto_map_columns(frame))
        result = normalize_table(mapped, 'statement')
        valid, errors = collect_errors(result)
        assert len(valid) == 2
        assert len(errors) == 0


def test_normalize_table_error_isolation() -> None:
    '''One corrupted row does not abort batch.'''
    frame = pd.DataFrame(
        {
            'Data': ['10/09/2026', 'invalida'],
            'Descrição': ['Pagamento X', 'Recebimento Y'],
            'Valor': ['-2500', 'abc'],
        }
    )
    mapped = mapping.apply_mapping(
        frame, {'data': 'Data', 'descricao': 'Descrição', 'valor': 'Valor'}
    )
    result = normalize_table(mapped, 'statement')
    assert len(result) == 2
    valid, errors = collect_errors(result)
    assert len(valid) == 1
    assert len(errors) == 1


def test_collect_errors_messages() -> None:
    '''Error table uses pt-BR columns and actionable messages.'''
    frame = pd.DataFrame(
        {
            'event_date': ['10/09/2026', '10/09/2026', '11/09/2026'],
            'description': ['A', 'B', 'C'],
            'amount': ['100', 'abc', '200'],
            'Data': ['10/09/2026', '10/09/2026', '11/09/2026'],
            'Descrição': ['A', 'B', 'C'],
            'Valor': ['100', 'abc', '200'],
        }
    )
    result = normalize_table(frame, 'statement')
    valid, errors = collect_errors(result)
    assert list(errors.columns) == ['Linha', 'Motivo', 'Orientação']
    assert len(valid) == 2
    assert len(errors) == 1
    motive = str(errors.iloc[0]['Motivo'])
    assert 'Valor inválido' in motive
    assert errors.iloc[0]['Linha'] == 3


def test_collect_errors_date_message() -> None:
    '''Date errors point to brazilian format.'''
    frame = pd.DataFrame(
        {
            'event_date': ['invalida'],
            'description': ['X'],
            'amount': ['100'],
            'Data': ['invalida'],
            'Descrição': ['X'],
            'Valor': ['100'],
        }
    )
    result = normalize_table(frame, 'ledger')
    _, errors = collect_errors(result)
    assert 'Data inválida' in str(errors.iloc[0]['Motivo'])
    assert 'DD/MM/AAAA' in str(errors.iloc[0]['Motivo'])


def test_normalize_date_numeric_invalid() -> None:
    '''Numeric dates are rejected.'''
    value, error = normalize_date(123)
    assert value is None
    assert error == 'DATA_INVALIDA'
    value, error = normalize_date(12.5)
    assert value is None
    assert error == 'DATA_INVALIDA'
    value, error = normalize_date(float('nan'))
    assert value is None
    assert error == 'DATA_INVALIDA'


def test_normalize_amount_decimal_bool_float() -> None:
    '''Direct numeric types preserve value or reject.'''
    value, error = normalize_amount(Decimal('10.5'))
    assert value == Decimal('10.5')
    assert error is None
    value, error = normalize_amount(True)
    assert value is None
    assert error == 'VALOR_INVALIDO'
    value, error = normalize_amount(2500.5)
    assert value == Decimal('2500.5')
    assert error is None
    value, error = normalize_amount(float('nan'))
    assert value is None
    assert error == 'VALOR_INVALIDO'
    value, error = normalize_amount(float('inf'))
    assert value is None
    assert error == 'VALOR_INVALIDO'
    value, error = normalize_amount('+2500')
    assert value == Decimal('2500')
    assert error is None
    value, error = normalize_amount('...')
    assert value is None
    assert error == 'VALOR_INVALIDO'


def test_normalize_amount_markers() -> None:
    '''Extended debit and credit markers resolve sign.'''
    value, error = normalize_amount('100 SAIDA')
    assert value == Decimal('-100')
    assert error is None
    value, error = normalize_amount('100 ENTRADA')
    assert value == Decimal('100')
    assert error is None
    value, error = normalize_amount('100 DEB')
    assert value == Decimal('-100')
    assert error is None
    value, error = normalize_amount('100 CRED')
    assert value == Decimal('100')
    assert error is None


def test_detect_sign_numeric_and_unknown() -> None:
    '''Numeric normalized values and unknown raws are handled.'''
    assert detect_sign(5, '5') == 1
    assert detect_sign(-5, '-5') == -1
    assert detect_sign(5.5, '5.5') == 1
    assert detect_sign('-2500', '-2500') == -1
    assert detect_sign('4800', '4800') == 1
    assert detect_sign(None, 'xyz') is None
    assert detect_sign(None, None) is None


def test_normalize_table_missing_columns() -> None:
    '''Missing internal columns flag coluna ausente.'''
    frame = pd.DataFrame({'Data': ['10/09/2026']})
    result = normalize_table(frame, 'statement')
    assert result.iloc[0]['error_code'] == 'COLUNA_AUSENTE'
    _, errors = collect_errors(result)
    assert 'Coluna obrigatória' in str(errors.iloc[0]['Motivo'])


def test_collect_errors_without_code_column() -> None:
    '''Tables without error code return empty error table.'''
    frame = pd.DataFrame({'Data': ['10/09/2026']})
    valid, errors = collect_errors(frame)
    assert len(valid) == 1
    assert list(errors.columns) == ['Linha', 'Motivo', 'Orientação']
    assert len(errors) == 0


def test_collect_errors_string_index() -> None:
    '''String index falls back to position for line number.'''
    frame = pd.DataFrame(
        {
            'event_date': ['10/09/2026'],
            'description': ['X'],
            'amount': ['abc'],
            'error_code': ['VALOR_INVALIDO'],
        },
        index=['a'],
    )
    _, errors = collect_errors(frame)
    assert errors.iloc[0]['Linha'] == 2


def test_collect_errors_unknown_code() -> None:
    '''Unknown codes use generic actionable message.'''
    frame = pd.DataFrame(
        {
            'event_date': ['10/09/2026'],
            'description': ['X'],
            'amount': ['100'],
            'error_code': ['OUTRO'],
        }
    )
    _, errors = collect_errors(frame)
    assert 'Erro na linha' in str(errors.iloc[0]['Motivo'])
