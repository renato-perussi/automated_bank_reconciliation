'''Matcher engine checks.'''

from decimal import Decimal

import pandas as pd
import pytest

import src.mapping as mapping
import src.matcher as matcher
from src.matcher import (
    build_params,
    calc_value_diff,
    find_candidates,
    score_candidates,
    score_description,
)
from src.normalize import normalize_table


def _make_frame(entries: list, source: str) -> pd.DataFrame:
    '''Build normalized frame from raw triples.'''
    frame = pd.DataFrame(entries, columns=['Data', 'Descrição', 'Valor'])
    mapped = mapping.apply_mapping(frame, mapping.auto_map_columns(frame))
    return normalize_table(mapped, source)


def _build_rows(count: int) -> list:
    '''Build distinct synthetic rows for perf check.'''
    rows: list = []
    for pos in range(count):
        day = 10 + (pos % 20)
        rows.append((f'{day:02d}/09/2026', f'alpha {pos}', str(1000 + pos)))
    return rows


def test_build_params_defaults() -> None:
    '''Defaults match config snapshot.'''
    params = build_params()
    assert params['date_tolerance_days'] == 2
    assert params['fuzzy_threshold'] == 85
    assert params['value_tolerance'] == Decimal('0.00')
    assert params['use_fuzzy'] is True


def test_build_params_custom() -> None:
    '''Custom valid params are preserved.'''
    params = build_params(
        date_tolerance_days=0, fuzzy_threshold=70, value_tolerance=Decimal('0.05'), use_fuzzy=False
    )
    assert params['date_tolerance_days'] == 0
    assert params['fuzzy_threshold'] == 70
    assert params['value_tolerance'] == Decimal('0.05')
    assert params['use_fuzzy'] is False


def test_build_params_tolerance_types() -> None:
    '''Int float str tolerances convert to Decimal.'''
    assert build_params(value_tolerance=1)['value_tolerance'] == Decimal('1')
    assert build_params(value_tolerance=0.05)['value_tolerance'] == Decimal('0.05')
    assert build_params(value_tolerance='0.05')['value_tolerance'] == Decimal('0.05')


def test_build_params_tolerance_without_upper_cap() -> None:
    '''Value tolerance above ten is accepted without ceiling.'''
    assert build_params(value_tolerance=Decimal('150.00'))['value_tolerance'] == Decimal('150.00')
    assert build_params(value_tolerance=Decimal('1000000'))['value_tolerance'] == Decimal(
        '1000000'
    )


def test_build_params_invalid_date() -> None:
    '''Day tolerance outside zero thirty raises pt-BR.'''
    with pytest.raises(ValueError, match='Tolerância de dias'):
        build_params(date_tolerance_days=-1)
    with pytest.raises(ValueError, match='Tolerância de dias'):
        build_params(date_tolerance_days=31)
    with pytest.raises(ValueError, match='Tolerância de dias'):
        build_params(date_tolerance_days=True)
    with pytest.raises(ValueError, match='Tolerância de dias'):
        build_params(date_tolerance_days='2')


def test_build_params_invalid_fuzzy() -> None:
    '''Fuzzy outside zero hundred raises pt-BR.'''
    with pytest.raises(ValueError, match='Similaridade mínima'):
        build_params(fuzzy_threshold=-1)
    with pytest.raises(ValueError, match='Similaridade mínima'):
        build_params(fuzzy_threshold=101)
    with pytest.raises(ValueError, match='Similaridade mínima'):
        build_params(fuzzy_threshold=False)


def test_build_params_invalid_value() -> None:
    '''Negative or invalid value tolerance raises pt-BR.'''
    with pytest.raises(ValueError, match='Tolerância de valor'):
        build_params(value_tolerance=Decimal('-0.01'))
    with pytest.raises(ValueError, match='Tolerância de valor'):
        build_params(value_tolerance='abc')
    with pytest.raises(ValueError, match='Tolerância de valor'):
        build_params(value_tolerance=True)


def test_build_params_invalid_flag() -> None:
    '''Non boolean fuzzy flag raises pt-BR.'''
    with pytest.raises(ValueError, match='Usar similaridade'):
        build_params(use_fuzzy='yes')


def test_calc_value_diff_exact() -> None:
    '''Decimal diff avoids float artefacts.'''
    assert calc_value_diff(Decimal('2500.00'), Decimal('2500.04')) == Decimal('0.04')
    assert calc_value_diff(Decimal('-2500'), Decimal('-2500')) == Decimal('0')
    assert calc_value_diff(Decimal('4800'), Decimal('4800')) == Decimal('0')


def test_calc_value_diff_types() -> None:
    '''Int and string inputs convert safely.'''
    assert calc_value_diff(100, 90) == Decimal('10')
    assert calc_value_diff('2500.00', '2500.00') == Decimal('0')


def test_score_description_both_empty() -> None:
    '''Empty pair scores full deterministically.'''
    assert score_description('', '') == 100
    assert score_description(None, None) == 100


def test_score_description_one_empty() -> None:
    '''Empty versus text scores zero.'''
    assert score_description('', 'fornecedor x') == 0
    assert score_description('pagamento x', '') == 0
    assert score_description(None, 'abc') == 0


def test_score_description_exact() -> None:
    '''Identical texts score full.'''
    assert score_description('cliente y', 'cliente y') == 100
    result = score_description('pagamento fornecedor x', 'pagamento fornecedor x')
    assert result == 100
    assert isinstance(result, int)


def test_score_description_token_set() -> None:
    '''Divergent wording scores below default threshold.'''
    result = score_description('pagamento fornecedor x', 'fornecedor x nf 1254')
    assert 0 <= result <= 100
    assert result < 85
    assert isinstance(result, int)


def test_find_case_b_default() -> None:
    '''Day diff one matches inside default window.'''
    statement = _make_frame([('11/09/2026', 'Recebimento Cliente Y', '4800')], 'statement')
    ledger = _make_frame([('12/09/2026', 'Cliente Y', '4800')], 'ledger')
    params = build_params()
    found = find_candidates(statement, ledger, params)
    assert len(found) == 1
    item = found[0]
    assert item['day_diff'] == 1
    assert item['value_diff'] == Decimal('0')
    assert item['description_score'] == 100


def test_find_case_b_zero_tolerance() -> None:
    '''Day diff one misses with zero window.'''
    statement = _make_frame([('11/09/2026', 'Recebimento Cliente Y', '4800')], 'statement')
    ledger = _make_frame([('12/09/2026', 'Cliente Y', '4800')], 'ledger')
    params = build_params(date_tolerance_days=0)
    found = find_candidates(statement, ledger, params)
    assert found == []


def test_find_case_d_signal_blocked() -> None:
    '''Opposite signs never match.'''
    statement = _make_frame([('10/09/2026', 'Pagamento X', '-2500')], 'statement')
    ledger = _make_frame([('10/09/2026', 'Pagamento X', '2500')], 'ledger')
    params = build_params()
    found = find_candidates(statement, ledger, params)
    assert found == []


def test_find_value_tolerance_inside() -> None:
    '''Cents inside tolerance produce candidate.'''
    statement = _make_frame([('10/09/2026', 'Fornecedor X', '2500.00')], 'statement')
    ledger = _make_frame([('10/09/2026', 'Fornecedor X', '2500.04')], 'ledger')
    params = build_params(value_tolerance=Decimal('0.05'))
    found = find_candidates(statement, ledger, params)
    assert len(found) == 1
    assert found[0]['value_diff'] == Decimal('0.04')


def test_find_value_tolerance_exact_blocks() -> None:
    '''Cents outside zero tolerance produce no candidate.'''
    statement = _make_frame([('10/09/2026', 'Fornecedor X', '2500.00')], 'statement')
    ledger = _make_frame([('10/09/2026', 'Fornecedor X', '2500.04')], 'ledger')
    params = build_params(value_tolerance=Decimal('0.00'))
    found = find_candidates(statement, ledger, params)
    assert found == []


def test_find_ignores_error_rows() -> None:
    '''Rows with error code never participate.'''
    statement = _make_frame(
        [('10/09/2026', 'Pagamento X', '-2500'), ('invalida', 'Recebimento Y', '100')], 'statement'
    )
    ledger = _make_frame([('10/09/2026', 'Pagamento X', '-2500')], 'ledger')
    params = build_params(fuzzy_threshold=0)
    found = find_candidates(statement, ledger, params)
    assert len(found) == 1
    assert found[0]['statement_idx'] == 0


def test_find_ignores_missing_fields() -> None:
    '''Missing date amount sign rows are skipped.'''
    frame = pd.DataFrame(
        {
            'normalized_date': [None, '2026-09-10'],
            'normalized_amount': [Decimal('100'), None],
            'normalized_value': [Decimal('100'), None],
            'normalized_description': ['alpha', 'beta'],
            'sign': [1, None],
            'error_code': [None, None],
        }
    )
    other = _make_frame([('10/09/2026', 'alpha', '100')], 'ledger')
    params = build_params()
    found = find_candidates(frame, other, params)
    assert found == []


def test_find_includes_score_range() -> None:
    '''Every candidate carries zero hundred score.'''
    statement = _make_frame([('10/09/2026', 'Pagamento Fornecedor X', '-2500')], 'statement')
    ledger = _make_frame([('10/09/2026', 'Fornecedor X NF 1254', '-2500')], 'ledger')
    params = build_params()
    found = find_candidates(statement, ledger, params)
    assert len(found) == 1
    score = found[0]['description_score']
    assert 0 <= score <= 100
    assert score < 85


def test_score_candidates_from_tuples() -> None:
    '''Tuple candidates enrich deterministically.'''
    statement = _make_frame([('10/09/2026', 'alpha beta', '100')], 'statement')
    ledger = _make_frame([('10/09/2026', 'alpha beta', '100')], 'ledger')
    raw = [(0, 0, 0, Decimal('0'))]
    scored = score_candidates(raw, statement, ledger)
    assert len(scored) == 1
    assert scored[0]['statement_idx'] == 0
    assert scored[0]['ledger_idx'] == 0
    assert scored[0]['description_score'] == 100


def test_score_candidates_sorted() -> None:
    '''Scored output sorts by indices.'''
    statement = _make_frame(
        [('10/09/2026', 'alpha', '100'), ('11/09/2026', 'alpha', '100')], 'statement'
    )
    ledger = _make_frame(
        [('10/09/2026', 'alpha', '100'), ('11/09/2026', 'alpha', '100')], 'ledger'
    )
    params = build_params(date_tolerance_days=5)
    found = find_candidates(statement, ledger, params)
    keys = [(item['statement_idx'], item['ledger_idx']) for item in found]
    assert keys == sorted(keys, key=lambda pair: (str(pair[0]), str(pair[1])))


def test_volume_warning_logged(caplog: object, monkeypatch: object) -> None:
    '''Large volume logs pt-BR warning.'''
    monkeypatch.setattr(matcher, 'MAX_ROWS_WARNING', 1)
    statement = _make_frame([('10/09/2026', 'alpha', '100')], 'statement')
    ledger = _make_frame([('10/09/2026', 'alpha', '100')], 'ledger')
    with caplog.at_level('WARNING'):
        find_candidates(statement, ledger, build_params())
    assert 'Volume alto: resultado pode demorar.' in caplog.text


def test_blocking_many_rows_fast() -> None:
    '''Distinct amounts use index without full cross join.'''
    statement_rows = _build_rows(300)
    ledger_rows = _build_rows(300)
    statement = _make_frame(statement_rows, 'statement')
    ledger = _make_frame(ledger_rows, 'ledger')
    params = build_params()
    found = find_candidates(statement, ledger, params)
    assert len(found) == 300
