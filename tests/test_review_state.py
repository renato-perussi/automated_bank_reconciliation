'''Review state red-green tests.'''

import pandas as pd


def test_confirm_moves_pair() -> None:
    '''Confirm adds to confirmed set.'''
    from src.review_state import confirm_pair_state
    state: dict = {}
    confirm_pair_state(state, 's0-l0', timestamp='2026-09-30T10:00:00')
    assert 's0-l0' in state['manual_confirmed']
    assert state['review_log'][0]['review_action'] == 'conciliada_manual'


def test_reject_moves_pair() -> None:
    '''Reject adds to rejected set.'''
    from src.review_state import reject_pair_state
    state: dict = {}
    reject_pair_state(state, 's1-l1', timestamp='2026-09-30T10:00:00')
    assert 's1-l1' in state['manual_rejected']


def test_undo_restores_sets() -> None:
    '''Undo removes last decision.'''
    from src.review_state import confirm_pair_state, undo_last_review_state
    state: dict = {}
    confirm_pair_state(state, 's0-l0', timestamp='2026-09-30T10:00:00')
    undo_last_review_state(state)
    assert 's0-l0' not in state['manual_confirmed']
    assert state['review_log'] == []


def test_adjusted_counts_adds_confirmed() -> None:
    '''Counts move potential to auto.'''
    from src.review_state import adjusted_counts
    results = {
        'auto': pd.DataFrame([{'a': 1}]),
        'potential': pd.DataFrame([{'a': 1}, {'a': 2}]),
        'pending': pd.DataFrame(),
        'divergent': pd.DataFrame(),
        'duplicate': pd.DataFrame(),
    }
    counts = adjusted_counts(results, {'x'}, set())
    assert counts[0] == 2
    assert counts[1] == 1


def test_apply_manual_kpis_recomputes() -> None:
    '''Kpis recompute from counts.'''
    from src.review_state import apply_manual_kpis
    kpis = {
        'pct_auto': 0.0,
        'pct_review': 0.0,
        'pct_pending': 0.0,
        'pct_divergent': 0.0,
        'exception_rate': 100.0,
    }
    updated = apply_manual_kpis(kpis, (2, 1, 0, 0, 0, 3, 1))
    assert updated['pct_auto'] > 0.0


def test_history_display_translates() -> None:
    '''History frame uses pt-BR labels.'''
    from src.review_state import history_display
    frame = history_display(
        [{'match_id': 's0-l0', 'review_action': 'conciliada_manual',
          'timestamp': '2026-09-30T10:00:00'}]
    )
    assert list(frame.columns) == ['Par ID', 'Ação', 'Data/Hora']
    assert frame.iloc[0]['Ação'] == 'Confirmada manualmente'


def test_filtered_review_rows_blocks_ids() -> None:
    '''Blocked ids disappear from review.'''
    from src.review_state import filtered_review_rows
    frame = pd.DataFrame([{'match_id': 'a'}, {'match_id': 'b'}])
    found = filtered_review_rows(frame, {'a'}, set())
    assert len(found) == 1


def test_ensure_keys_undo_empty_counts_none() -> None:
    '''Keys init undo empty none counts safe.'''
    from src.review_state import adjusted_counts, ensure_review_keys, undo_last_review_state
    state: dict = {}
    ensure_review_keys(state)
    assert state['review_log'] == []
    assert undo_last_review_state(state) is None
    assert undo_last_review_state({}) is None
    assert adjusted_counts(None, set(), set()) == (0, 0, 0, 0, 0, 0, 0)


def test_apply_kpis_zero_history_fallback() -> None:
    '''Zero unified keeps kpis fallback label.'''
    from src.review_state import apply_manual_kpis, history_label, history_moment
    kpis = {'pct_auto': 1.0}
    assert apply_manual_kpis(kpis, (0, 0, 0, 0, 0, 0, 0)) == kpis
    assert history_label('unknown-code') == 'unknown-code'
    assert history_moment('not-a-date') == 'not-a-date'
    assert history_moment(None) == 'None'


def test_filtered_no_match_confirmed_empty() -> None:
    '''Missing match column empty confirmed safe.'''
    from src.review_state import confirmed_rows, filtered_review_rows
    frame = pd.DataFrame([{'other': 1}])
    assert len(filtered_review_rows(frame, set(), set())) == 1
    assert len(confirmed_rows(None, {'a'})) == 0
    assert len(confirmed_rows({'potential': pd.DataFrame()}, {'a'})) == 0
    results = {'potential': pd.DataFrame([{'match_id': 'a'}])}
    assert len(confirmed_rows(results, set())) == 0
    assert len(confirmed_rows(results, {'a'})) == 1


def test_active_frame_branches() -> None:
    '''None auto potential divergent branches.'''
    import pandas as pd

    from src.review_state import active_frame
    assert len(active_frame(None, 'auto', set(), set(), None)) == 0
    auto = pd.DataFrame([{'match_id': 'k'}])
    assert len(active_frame(auto, 'auto', set(), set(), None)) == 1
    results = {'potential': pd.DataFrame([{'match_id': 'k'}])}
    grown = active_frame(auto, 'auto', {'k'}, set(), results)
    assert len(grown) == 2
    no_id = pd.DataFrame([{'other': 1}])
    assert len(active_frame(no_id, 'potential', set(), set(), None)) == 1
    pot = pd.DataFrame([{'match_id': 'a'}, {'match_id': 'b'}])
    assert len(active_frame(pot, 'potential', {'a'}, set(), None)) == 1
    assert len(active_frame(pot, 'divergent', set(), set(), None)) == 2
