'''Classification split parity checks.'''

from decimal import Decimal

import pandas as pd

import src.mapping as mapping
from src.classification.tables import build_result_tables as split_tables
from src.classifier import build_result_tables as facade_tables
from src.matcher import build_params
from src.normalize import normalize_table


def _make_frame(entries: list, source: str) -> pd.DataFrame:
    '''Build normalized frame from raw triples.'''
    frame = pd.DataFrame(entries, columns=['Data', 'Descrição', 'Valor'])
    mapped = mapping.apply_mapping(frame, mapping.auto_map_columns(frame))
    return normalize_table(mapped, source)


def test_tables_identical() -> None:
    '''Facade and split tables produce identical frames.'''
    statement = _make_frame(
        [
            ('10/09/2026', 'Pagamento Fornecedor X', '-2500'),
            ('11/09/2026', 'Recebimento Cliente Y', '4800'),
        ],
        'statement',
    )
    ledger = _make_frame(
        [
            ('10/09/2026', 'Fornecedor X NF 1254', '-2500'),
            ('12/09/2026', 'Cliente Y', '4800'),
        ],
        'ledger',
    )
    params = build_params()
    first = facade_tables(statement, ledger, params)
    second = split_tables(statement, ledger, params)
    for key in ('auto', 'potential', 'pending', 'divergent', 'duplicate'):
        pd.testing.assert_frame_equal(first[key], second[key])


def test_case_b_auto() -> None:
    '''Day diff one auto with defaults.'''
    statement = _make_frame([('11/09/2026', 'Recebimento Cliente Y', '4800')], 'statement')
    ledger = _make_frame([('12/09/2026', 'Cliente Y', '4800')], 'ledger')
    tables = facade_tables(statement, ledger, build_params())
    assert len(tables['auto']) == 1


def test_case_d_signal_pending() -> None:
    '''Opposite signs yield pending signal motive.'''
    statement = _make_frame([('10/09/2026', 'Pagamento X', '-2500')], 'statement')
    ledger = _make_frame([('10/09/2026', 'Pagamento X', '2500')], 'ledger')
    tables = facade_tables(statement, ledger, build_params())
    assert len(tables['auto']) == 0
    assert 'sinal_bloqueado' in set(tables['pending']['reason'].tolist())


def test_case_cents_and_ambiguity() -> None:
    '''Cents never auto and ambiguity never auto.'''
    statement = _make_frame([('10/09/2026', 'Fornecedor X', '2500.00')], 'statement')
    ledger = _make_frame([('10/09/2026', 'Fornecedor X', '2500.04')], 'ledger')
    tables = facade_tables(statement, ledger, build_params(value_tolerance=Decimal('0.05')))
    assert len(tables['auto']) == 0
    assert tables['potential'].iloc[0]['reason'] == 'divergencia_centavos'
    statement_two = _make_frame([('10/09/2026', 'Fornecedor X', '-1500')], 'statement')
    ledger_two = _make_frame(
        [
            ('10/09/2026', 'Fornecedor X', '-1500'),
            ('10/09/2026', 'ZZZ QQQ WWW totalmente diferente', '-1500'),
        ],
        'ledger',
    )
    tables_two = facade_tables(statement_two, ledger_two, build_params())
    assert len(tables_two['auto']) == 0
    assert 'ambiguidade_multipla' in set(tables_two['potential']['reason'].tolist())
