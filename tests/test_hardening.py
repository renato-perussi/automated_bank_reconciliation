'''Hardening checks for security resilience and PRD cases.'''

import inspect
import logging
import time
from decimal import Decimal
from pathlib import Path

import pandas as pd

import app as app_module
import src.loader as loader
import src.mapping as mapping
from scripts.bench import _warn_volume
from src.classifier import build_result_tables
from src.config import MAX_ROWS_WARNING
from src.loader import get_preview, load_table
from src.matcher import build_params
from src.normalize import normalize_table
from src.validate import collect_errors


def _make_frame(entries: list, source: str) -> pd.DataFrame:
    '''Build normalized frame from raw triples.'''
    frame = pd.DataFrame(entries, columns=['Data', 'Descrição', 'Valor'])
    mapped = mapping.apply_mapping(frame, mapping.auto_map_columns(frame))
    return normalize_table(mapped, source)


def test_reject_path_traversal() -> None:
    '''Traversal names are blocked with pt-BR message.'''
    try:
        load_table(Path('../../etc/passwd.csv'))
        assert False
    except ValueError as exc:
        assert 'Nome de arquivo inválido' in str(exc)


def test_reject_oversize(monkeypatch: object, tmp_path: Path) -> None:
    '''Files above limit are rejected with pt-BR message.'''
    target = tmp_path / 'sample.csv'
    target.write_text('Data,Descrição,Valor\n10/09/2026,X,100\n', encoding='utf-8')
    monkeypatch.setattr(loader, 'MAX_FILE_SIZE_MB', 0)
    try:
        load_table(target)
        assert False
    except ValueError as exc:
        assert 'Arquivo acima de 20 MB' in str(exc)


def test_corrupted_row_does_not_abort() -> None:
    '''Single bad line isolates without aborting batch.'''
    frame = pd.DataFrame(
        {
            'Data': ['10/09/2026', '10/09/2026', '11/09/2026'],
            'Descrição': ['Pagamento X', 'Recebimento Y', 'Servico Z'],
            'Valor': ['-2500', 'abc', '4800'],
        }
    )
    chosen = {'data': 'Data', 'descricao': 'Descrição', 'valor': 'Valor'}
    mapped = mapping.apply_mapping(frame, chosen)
    result = normalize_table(mapped, 'statement')
    assert len(result) == 3
    valid, errors = collect_errors(result)
    assert len(valid) == 2
    assert len(errors) == 1
    assert 'Valor inválido' in str(errors.iloc[0]['Motivo'])


def test_idempotent_runs() -> None:
    '''Two runs with same inputs produce equal tables.'''
    statement = _make_frame(
        [('10/09/2026', 'Pagamento Fornecedor X', '-2500'), ('11/09/2026', 'Cliente Y', '4800')],
        'statement',
    )
    ledger = _make_frame(
        [('10/09/2026', 'Fornecedor X NF 1254', '-2500'), ('12/09/2026', 'Cliente Y', '4800')],
        'ledger',
    )
    params = build_params()
    first = build_result_tables(statement, ledger, params)
    second = build_result_tables(statement, ledger, params)
    for key in ('auto', 'potential', 'pending', 'divergent', 'duplicate'):
        pd.testing.assert_frame_equal(first[key], second[key])


def test_case_a_exact_divergent_text() -> None:
    '''Case A goes review when fuzzy below threshold.'''
    statement = _make_frame([('10/09/2026', 'Pagamento Fornecedor X', '-2500')], 'statement')
    ledger = _make_frame([('10/09/2026', 'Fornecedor X NF 1254', '-2500')], 'ledger')
    tables = build_result_tables(statement, ledger, build_params())
    assert len(tables['auto']) == 0
    assert len(tables['potential']) == 1
    assert tables['potential'].iloc[0]['day_diff'] == 0
    assert tables['potential'].iloc[0]['value_diff'] == Decimal('0')


def test_case_b_tolerance_auto() -> None:
    '''Case B auto with default day window.'''
    statement = _make_frame([('11/09/2026', 'Recebimento Cliente Y', '4800')], 'statement')
    ledger = _make_frame([('12/09/2026', 'Cliente Y', '4800')], 'ledger')
    tables = build_result_tables(statement, ledger, build_params())
    assert len(tables['auto']) == 1
    assert tables['auto'].iloc[0]['day_diff'] == 1


def test_case_c_value_trap_no_auto() -> None:
    '''Case C distinct same values never auto.'''
    statement = _make_frame(
        [('10/09/2026', 'Pagamento Alfa', '-1500'), ('18/09/2026', 'Pagamento Beta', '-1500')],
        'statement',
    )
    ledger = _make_frame(
        [('11/09/2026', 'Alfa NF 1', '-1500'), ('19/09/2026', 'Beta NF 2', '-1500')], 'ledger'
    )
    tables = build_result_tables(statement, ledger, build_params(fuzzy_threshold=95))
    assert len(tables['auto']) == 0


def test_case_d_signal_blocked() -> None:
    '''Case D opposite signs stay pending.'''
    statement = _make_frame([('10/09/2026', 'Pagamento X', '-2500')], 'statement')
    ledger = _make_frame([('10/09/2026', 'Pagamento X', '2500')], 'ledger')
    tables = build_result_tables(statement, ledger, build_params())
    assert len(tables['auto']) == 0
    assert len(tables['potential']) == 0
    assert len(tables['pending']) == 2


def test_matrix_loads(fixture_paths: dict) -> None:
    '''Matrix fixtures load on linux without crash.'''
    base = Path(fixture_paths['matrix'])
    for name in ('latin1_ponto_virgula.csv', 'header_minusculo.csv', 'valor_parenteses.csv'):
        frame, _ = load_table(base / name)
        assert len(frame) > 0
    for name in ('data_iso.csv',):
        frame, _ = load_table(base / name)
        mapped = mapping.apply_mapping(frame, mapping.auto_map_columns(frame))
        result = normalize_table(mapped, 'statement')
        valid, _ = collect_errors(result)
        assert len(valid) == 2


def test_preview_under_three_seconds() -> None:
    '''Preview returns five rows under three seconds.'''
    rows = [{'Data': '10/09/2026', 'Descrição': 'Item', 'Valor': '100'}]
    rows = rows * 200
    frame = pd.DataFrame(rows)
    started = time.perf_counter()
    preview = get_preview(frame, 5)
    elapsed = time.perf_counter() - started
    assert len(preview) == 5
    assert elapsed < 3.0


def test_high_volume_warning(caplog: object) -> None:
    '''Volume above twenty thousand warns pt-BR.'''
    assert MAX_ROWS_WARNING == 20000
    with caplog.at_level(logging.WARNING):
        _warn_volume(MAX_ROWS_WARNING + 1, 0)
    assert any('Volume alto' in str(item.message) for item in caplog.records)


def test_seven_step_flow_documented() -> None:
    '''Seven step flow stays documented and wired.'''
    text = Path('README.md').read_text(encoding='utf-8')
    assert 'Fluxo em 7 passos' in text
    assert 'Baixar relatório em Excel' in text
    assert 'Baixar só exceções' in text
    source = inspect.getsource(app_module.main)
    assert source.count('render_') >= 7
