'''Classifier engine checks.'''

from decimal import Decimal

import pandas as pd

import src.mapping as mapping
from src.classifier import (
    STATUS_LABEL_PT,
    build_result_tables,
    classify_match,
    detect_duplicates,
    resolve_ambiguity,
)
from src.loader import load_table
from src.matcher import build_params
from src.normalize import normalize_table


def _make_frame(entries: list, source: str) -> pd.DataFrame:
    '''Build normalized frame from raw triples.'''
    frame = pd.DataFrame(entries, columns=['Data', 'Descrição', 'Valor'])
    mapped = mapping.apply_mapping(frame, mapping.auto_map_columns(frame))
    return normalize_table(mapped, source)


def _load_normalized(target: object, source: str) -> pd.DataFrame:
    '''Load fixture file into normalized form.'''
    frame, _ = load_table(target)
    mapped = mapping.apply_mapping(frame, mapping.auto_map_columns(frame))
    return normalize_table(mapped, source)


def test_status_labels_pt() -> None:
    '''Internal states map to pt-BR labels.'''
    assert STATUS_LABEL_PT['auto'] == 'Conciliada'
    assert STATUS_LABEL_PT['potential'] == 'Para revisão'
    assert STATUS_LABEL_PT['pending'] == 'Pendente'
    assert STATUS_LABEL_PT['divergent'] == 'Divergente'
    assert STATUS_LABEL_PT['duplicate'] == 'Duplicada'


def test_detect_duplicates_fixture(fixture_paths: dict) -> None:
    '''Identical rows flag both indices.'''
    frame = _load_normalized(fixture_paths['duplicates'], 'statement')
    params = build_params()
    found = detect_duplicates(frame, params)
    assert found == {0, 1}


def test_detect_duplicates_none() -> None:
    '''Distinct amounts yield empty set.'''
    frame = _make_frame(
        [('10/09/2026', 'alpha', '-1500'), ('11/09/2026', 'beta', '-1600')], 'statement'
    )
    assert detect_duplicates(frame, build_params()) == set()


def test_detect_duplicates_empty() -> None:
    '''Empty frame yields empty set.'''
    frame = pd.DataFrame(columns=['Data'])
    assert detect_duplicates(frame, build_params()) == set()


def test_detect_duplicates_date_outside() -> None:
    '''Same value outside date window is not duplicate.'''
    frame = _make_frame(
        [('10/09/2026', 'Fornecedor Z', '-1500'), ('20/09/2026', 'Fornecedor Z', '-1500')],
        'statement',
    )
    assert detect_duplicates(frame, build_params()) == set()


def test_detect_duplicates_low_score() -> None:
    '''Same value date but dissimilar text is not duplicate.'''
    frame = _make_frame(
        [
            ('10/09/2026', 'pagamento fornecedor alfa', '-1500'),
            ('10/09/2026', 'xyz qqq www', '-1500'),
        ],
        'statement',
    )
    assert detect_duplicates(frame, build_params()) == set()


def test_detect_duplicates_sign_different() -> None:
    '''Opposite signs never duplicate.'''
    frame = _make_frame(
        [('10/09/2026', 'alpha', '-1500'), ('10/09/2026', 'alpha', '1500')], 'statement'
    )
    assert detect_duplicates(frame, build_params()) == set()


def test_classify_auto_exact() -> None:
    '''Exact value date high fuzzy yields auto.'''
    candidate = {'day_diff': 0, 'value_diff': Decimal('0'), 'description_score': 100}
    result = classify_match(candidate, build_params())
    assert result['status'] == 'auto'
    assert result['rule_id'] == 'RN-06'


def test_classify_potential_fuzzy_low() -> None:
    '''Score below threshold yields potential review.'''
    candidate = {'day_diff': 0, 'value_diff': Decimal('0'), 'description_score': 75}
    result = classify_match(candidate, build_params())
    assert result['status'] == 'potential'
    assert result['rule_id'] == 'RN-05'
    assert result['reason'] == 'descricao_baixa_similaridade'


def test_classify_divergent_exact_low() -> None:
    '''Very low score yields divergent.'''
    candidate = {'day_diff': 0, 'value_diff': Decimal('0'), 'description_score': 10}
    result = classify_match(candidate, build_params())
    assert result['status'] == 'divergent'
    assert result['rule_id'] == 'RN-05'


def test_classify_pending_none() -> None:
    '''Missing candidate yields pending base rule.'''
    result = classify_match(None, build_params())
    assert result['status'] == 'pending'
    assert result['rule_id'] == 'RN-01'
    assert result['reason'] == 'sem_candidato'


def test_classify_pending_date_out() -> None:
    '''Day beyond window yields pending date rule.'''
    candidate = {'day_diff': 5, 'value_diff': Decimal('0'), 'description_score': 100}
    result = classify_match(candidate, build_params())
    assert result['status'] == 'pending'
    assert result['rule_id'] == 'RN-02'


def test_classify_pending_value_out() -> None:
    '''Value beyond tolerance yields pending value rule.'''
    candidate = {'day_diff': 0, 'value_diff': Decimal('0.10'), 'description_score': 100}
    result = classify_match(candidate, build_params(value_tolerance=Decimal('0.05')))
    assert result['status'] == 'pending'
    assert result['rule_id'] == 'RN-08'


def test_classify_duplicate_blocks() -> None:
    '''Duplicate flag forces duplicate state.'''
    candidate = {'day_diff': 0, 'value_diff': Decimal('0'), 'description_score': 100}
    result = classify_match(candidate, build_params(), False, True)
    assert result['status'] == 'duplicate'
    assert result['rule_id'] == 'RN-04'


def test_classify_ambiguity_never_auto() -> None:
    '''Ambiguous perfect match stays potential.'''
    candidate = {'day_diff': 0, 'value_diff': Decimal('0'), 'description_score': 100}
    result = classify_match(candidate, build_params(), True, False)
    assert result['status'] == 'potential'
    assert result['rule_id'] == 'RN-07'
    assert result['reason'] == 'ambiguidade_multipla'


def test_classify_cents_potential() -> None:
    '''Cents inside tolerance yield review cents motive.'''
    candidate = {'day_diff': 0, 'value_diff': Decimal('0.04'), 'description_score': 100}
    params = build_params(value_tolerance=Decimal('0.05'))
    result = classify_match(candidate, params)
    assert result['status'] == 'potential'
    assert result['rule_id'] == 'RN-08'
    assert result['reason'] == 'divergencia_centavos'


def test_classify_cents_divergent_low_fuzzy() -> None:
    '''Cents plus dissimilar text yield divergent.'''
    candidate = {'day_diff': 0, 'value_diff': Decimal('0.04'), 'description_score': 10}
    params = build_params(value_tolerance=Decimal('0.05'))
    result = classify_match(candidate, params)
    assert result['status'] == 'divergent'
    assert result['rule_id'] == 'RN-08'


def test_classify_fuzzy_off_auto() -> None:
    '''Disabled fuzzy ignores description for auto.'''
    candidate = {'day_diff': 1, 'value_diff': Decimal('0'), 'description_score': 0}
    params = build_params(use_fuzzy=False)
    result = classify_match(candidate, params)
    assert result['status'] == 'auto'
    assert result['rule_id'] == 'RN-06'


def test_classify_fuzzy_off_cents() -> None:
    '''Disabled fuzzy with cents yields potential.'''
    candidate = {'day_diff': 0, 'value_diff': Decimal('0.04'), 'description_score': 0}
    params = build_params(value_tolerance=Decimal('0.05'), use_fuzzy=False)
    result = classify_match(candidate, params)
    assert result['status'] == 'potential'
    assert result['reason'] == 'divergencia_centavos'


def test_classify_tuple_candidate() -> None:
    '''Tuple form classifies like dict form.'''
    candidate = (0, 0, 0, Decimal('0'), 100)
    result = classify_match(candidate, build_params())
    assert result['status'] == 'auto'


def test_resolve_empty() -> None:
    '''Empty input resolves empty outputs.'''
    winners, losers = resolve_ambiguity([])
    assert winners == []
    assert losers == []


def test_resolve_single() -> None:
    '''Single candidate has no ambiguity.'''
    item = {
        'statement_idx': 0,
        'ledger_idx': 0,
        'day_diff': 0,
        'value_diff': Decimal('0'),
        'description_score': 100,
    }
    winners, losers = resolve_ambiguity([item])
    assert winners == [item]
    assert losers == []


def test_resolve_statement_ambiguity() -> None:
    '''One statement two ledgers picks smallest day.'''
    first = {
        'statement_idx': 0,
        'ledger_idx': 0,
        'day_diff': 2,
        'value_diff': Decimal('0'),
        'description_score': 90,
    }
    second = {
        'statement_idx': 0,
        'ledger_idx': 1,
        'day_diff': 0,
        'value_diff': Decimal('0'),
        'description_score': 80,
    }
    winners, losers = resolve_ambiguity([first, second])
    assert len(winners) == 1
    assert len(losers) == 1
    assert winners[0]['ledger_idx'] == 1
    assert losers[0]['ledger_idx'] == 0


def test_resolve_tie_highest_score() -> None:
    '''Equal days pick highest score.'''
    first = {
        'statement_idx': 0,
        'ledger_idx': 0,
        'day_diff': 1,
        'value_diff': Decimal('0'),
        'description_score': 70,
    }
    second = {
        'statement_idx': 0,
        'ledger_idx': 1,
        'day_diff': 1,
        'value_diff': Decimal('0'),
        'description_score': 95,
    }
    winners, losers = resolve_ambiguity([first, second])
    assert winners[0]['ledger_idx'] == 1


def test_resolve_ledger_ambiguity() -> None:
    '''Two statements one ledger picks best.'''
    first = {
        'statement_idx': 0,
        'ledger_idx': 5,
        'day_diff': 0,
        'value_diff': Decimal('0'),
        'description_score': 60,
    }
    second = {
        'statement_idx': 1,
        'ledger_idx': 5,
        'day_diff': 0,
        'value_diff': Decimal('0'),
        'description_score': 99,
    }
    winners, losers = resolve_ambiguity([first, second])
    assert winners[0]['statement_idx'] == 1
    assert losers[0]['statement_idx'] == 0


def test_build_case_a_potential() -> None:
    '''Exact value date divergent text goes review.'''
    statement = _make_frame([('10/09/2026', 'Pagamento Fornecedor X', '-2500')], 'statement')
    ledger = _make_frame([('10/09/2026', 'Fornecedor X NF 1254', '-2500')], 'ledger')
    tables = build_result_tables(statement, ledger, build_params())
    assert len(tables['auto']) == 0
    assert len(tables['potential']) == 1
    assert tables['potential'].iloc[0]['rule_id'] == 'RN-05'


def test_build_case_a_auto_low_threshold() -> None:
    '''Reduced threshold elevates divergent text to auto.'''
    statement = _make_frame([('10/09/2026', 'Pagamento Fornecedor X', '-2500')], 'statement')
    ledger = _make_frame([('10/09/2026', 'Fornecedor X NF 1254', '-2500')], 'ledger')
    tables = build_result_tables(statement, ledger, build_params(fuzzy_threshold=70))
    assert len(tables['auto']) == 1
    assert tables['auto'].iloc[0]['rule_id'] == 'RN-06'


def test_build_case_b_auto() -> None:
    '''Day diff one auto with defaults.'''
    statement = _make_frame([('11/09/2026', 'Recebimento Cliente Y', '4800')], 'statement')
    ledger = _make_frame([('12/09/2026', 'Cliente Y', '4800')], 'ledger')
    tables = build_result_tables(statement, ledger, build_params())
    assert len(tables['auto']) == 1
    assert tables['auto'].iloc[0]['day_diff'] == 1


def test_build_case_b_zero_tolerance() -> None:
    '''Zero window blocks tolerance match.'''
    statement = _make_frame([('11/09/2026', 'Recebimento Cliente Y', '4800')], 'statement')
    ledger = _make_frame([('12/09/2026', 'Cliente Y', '4800')], 'ledger')
    tables = build_result_tables(statement, ledger, build_params(date_tolerance_days=0))
    assert len(tables['auto']) == 0
    assert len(tables['pending']) == 2


def test_build_case_d_signal_pending() -> None:
    '''Opposite signs yield pending signal motive.'''
    statement = _make_frame([('10/09/2026', 'Pagamento X', '-2500')], 'statement')
    ledger = _make_frame([('10/09/2026', 'Pagamento X', '2500')], 'ledger')
    tables = build_result_tables(statement, ledger, build_params())
    assert len(tables['auto']) == 0
    assert len(tables['potential']) == 0
    assert len(tables['pending']) == 2
    reasons = set(tables['pending']['reason'].tolist())
    assert 'sinal_bloqueado' in reasons


def test_build_trap_zero_auto() -> None:
    '''Two distinct same values never auto.'''
    statement = _make_frame(
        [('10/09/2026', 'Pagamento Alfa', '-1500'), ('18/09/2026', 'Pagamento Beta', '-1500')],
        'statement',
    )
    ledger = _make_frame(
        [('11/09/2026', 'Alfa NF 1', '-1500'), ('19/09/2026', 'Beta NF 2', '-1500')], 'ledger'
    )
    tables = build_result_tables(statement, ledger, build_params(fuzzy_threshold=95))
    assert len(tables['auto']) == 0


def test_build_ambiguity_zero_auto() -> None:
    '''One statement two ledgers never auto.'''
    statement = _make_frame([('10/09/2026', 'Fornecedor X', '-1500')], 'statement')
    ledger = _make_frame(
        [
            ('10/09/2026', 'Fornecedor X', '-1500'),
            ('10/09/2026', 'ZZZ QQQ WWW totalmente diferente', '-1500'),
        ],
        'ledger',
    )
    tables = build_result_tables(statement, ledger, build_params())
    assert len(tables['auto']) == 0
    assert len(tables['potential']) >= 1
    assert 'ambiguidade_multipla' in set(tables['potential']['reason'].tolist())


def test_build_cents_potential() -> None:
    '''Cents inside tolerance yield potential cents motive.'''
    statement = _make_frame([('10/09/2026', 'Fornecedor X', '2500.00')], 'statement')
    ledger = _make_frame([('10/09/2026', 'Fornecedor X', '2500.04')], 'ledger')
    params = build_params(value_tolerance=Decimal('0.05'))
    tables = build_result_tables(statement, ledger, params)
    assert len(tables['auto']) == 0
    assert len(tables['potential']) == 1
    assert tables['potential'].iloc[0]['reason'] == 'divergencia_centavos'
    assert tables['potential'].iloc[0]['rule_id'] == 'RN-08'


def test_build_cents_exact_blocks() -> None:
    '''Cents with zero tolerance yield pending only.'''
    statement = _make_frame([('10/09/2026', 'Fornecedor X', '2500.00')], 'statement')
    ledger = _make_frame([('10/09/2026', 'Fornecedor X', '2500.04')], 'ledger')
    tables = build_result_tables(statement, ledger, build_params())
    assert len(tables['auto']) == 0
    assert len(tables['potential']) == 0
    assert len(tables['pending']) == 2


def test_build_duplicate_no_auto(fixture_paths: dict) -> None:
    '''Duplicate base blocks auto and lists duplicates.'''
    dup = _load_normalized(fixture_paths['duplicates'], 'statement')
    ledger = _make_frame([('10/09/2026', 'Pagamento Fornecedor Z', '-1500')], 'ledger')
    tables = build_result_tables(dup, ledger, build_params())
    assert len(tables['auto']) == 0
    assert len(tables['duplicate']) == 2
    assert set(tables['duplicate']['rule_id'].tolist()) == {'RN-04'}


def test_build_five_tables_shape() -> None:
    '''Pipeline returns five auditable frames.'''
    statement = _make_frame([('10/09/2026', 'Pagamento Fornecedor X', '-2500')], 'statement')
    ledger = _make_frame([('10/09/2026', 'Fornecedor X NF 1254', '-2500')], 'ledger')
    tables = build_result_tables(statement, ledger, build_params())
    assert set(tables.keys()) == {'auto', 'potential', 'pending', 'divergent', 'duplicate'}
    for key in ('auto', 'potential', 'pending', 'divergent', 'duplicate'):
        frame = tables[key]
        for field in (
            'statement_idx',
            'ledger_idx',
            'match_id',
            'day_diff',
            'value_diff',
            'description_score',
            'rule_id',
            'reason',
            'params_snapshot',
        ):
            assert field in list(frame.columns)
    snapshot = tables['potential'].iloc[0]['params_snapshot']
    assert snapshot['APP_VERSION'] == '1.0.0'
    assert snapshot['date_tolerance_days'] == 2
    assert tables['potential'].iloc[0]['match_id'] == 's0-l0'


def test_build_idempotent() -> None:
    '''Same inputs produce identical tables.'''
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


def test_build_divergent_path() -> None:
    '''Very dissimilar text lands divergent table.'''
    statement = _make_frame([('10/09/2026', 'aaaaaaaaaaaaaaaa', '-2500')], 'statement')
    ledger = _make_frame([('10/09/2026', 'zzzzzzzzzzzzzzzz', '-2500')], 'ledger')
    tables = build_result_tables(statement, ledger, build_params())
    assert len(tables['auto']) == 0
    assert len(tables['divergent']) == 1
    assert tables['divergent'].iloc[0]['rule_id'] == 'RN-05'


def test_build_fuzzy_off_unique_auto() -> None:
    '''Disabled fuzzy with unique pair auto.'''
    statement = _make_frame([('10/09/2026', 'Pagamento X', '-2500')], 'statement')
    ledger = _make_frame([('10/09/2026', 'Totalmente diferente', '-2500')], 'ledger')
    tables = build_result_tables(statement, ledger, build_params(use_fuzzy=False))
    assert len(tables['auto']) == 1


def test_classify_invalid_value_pending() -> None:
    '''Unparsable value diff yields pending.'''
    candidate = {'day_diff': 0, 'value_diff': 'xyz', 'description_score': 100}
    result = classify_match(candidate, build_params())
    assert result['status'] == 'pending'


def test_classify_missing_score_fuzzy() -> None:
    '''Missing score with fuzzy yields divergent.'''
    candidate = {'day_diff': 0, 'value_diff': Decimal('0'), 'description_score': None}
    result = classify_match(candidate, build_params())
    assert result['status'] == 'divergent'


def test_build_prd_fixtures(fixture_paths: dict) -> None:
    '''Reference fixtures produce one potential one auto.'''
    statement = _load_normalized(fixture_paths['statement'], 'statement')
    ledger = _load_normalized(fixture_paths['ledger'], 'ledger')
    tables = build_result_tables(statement, ledger, build_params())
    assert len(tables['auto']) == 1
    assert len(tables['potential']) == 1
    assert len(tables['duplicate']) == 0


def test_build_cross_index_no_collision() -> None:
    '''Cross index match keeps opposite sides pending.'''
    statement = _make_frame(
        [('10/09/2026', 'Fornecedor X', '100'), ('10/09/2026', 'Fornecedor Y', '200')],
        'statement',
    )
    ledger = _make_frame(
        [('10/09/2026', 'Fornecedor Z', '300'), ('10/09/2026', 'Fornecedor X', '100')],
        'ledger',
    )
    tables = build_result_tables(statement, ledger, build_params())
    assert len(tables['auto']) == 1
    assert tables['auto'].iloc[0]['statement_idx'] == 0
    assert tables['auto'].iloc[0]['ledger_idx'] == 1
    assert tables['auto'].iloc[0]['match_id'] == 's0-l1'
    assert len(tables['pending']) == 2
    assert set(tables['pending']['source'].tolist()) == {'statement', 'ledger'}
    statement_pending = tables['pending'][tables['pending']['source'] == 'statement']
    ledger_pending = tables['pending'][tables['pending']['source'] == 'ledger']
    assert len(statement_pending) == 1
    assert len(ledger_pending) == 1
    assert statement_pending.iloc[0]['statement_idx'] == 1
    assert ledger_pending.iloc[0]['ledger_idx'] == 0


def test_build_statement_only_pending() -> None:
    '''Single statement row without ledger stays pending.'''
    statement = _make_frame([('10/09/2026', 'Fornecedor X', '100')], 'statement')
    ledger = _make_frame([], 'ledger')
    tables = build_result_tables(statement, ledger, build_params())
    assert len(tables['auto']) == 0
    assert len(tables['pending']) == 1
    assert tables['pending'].iloc[0]['source'] == 'statement'
    assert tables['pending'].iloc[0]['statement_idx'] == 0


def test_build_ledger_only_pending() -> None:
    '''Single ledger row without statement stays pending.'''
    statement = _make_frame([], 'statement')
    ledger = _make_frame([('10/09/2026', 'Fornecedor X', '100')], 'ledger')
    tables = build_result_tables(statement, ledger, build_params())
    assert len(tables['auto']) == 0
    assert len(tables['pending']) == 1
    assert tables['pending'].iloc[0]['source'] == 'ledger'
    assert tables['pending'].iloc[0]['ledger_idx'] == 0
