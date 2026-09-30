'''Intra base duplicate detection and table.'''

import pandas as pd

from src.matcher import find_candidates

_MATCH_COLUMNS = [
    'statement_idx',
    'ledger_idx',
    'match_id',
    'day_diff',
    'value_diff',
    'description_score',
    'rule_id',
    'reason',
    'params_snapshot',
    'source',
]


def detect_duplicates(frame: pd.DataFrame, params: dict) -> set:
    '''Detect intra base duplicates reusing blocking matcher.'''
    if frame is None or len(frame) == 0:
        return set()
    pairs = find_candidates(frame, frame, params)
    found: set = set()
    for item in pairs:
        first = item.get('statement_idx')
        second = item.get('ledger_idx')
        if first == second:
            continue
        score = item.get('description_score', 0)
        if score is None:
            score = 0
        if int(score) >= 95:
            found.add(first)
            found.add(second)
    return found


def _empty_frame() -> pd.DataFrame:
    '''Build empty result frame with standard columns.'''
    return pd.DataFrame(columns=_MATCH_COLUMNS)


def _build_duplicate_table(
    statement_df: pd.DataFrame,
    ledger_df: pd.DataFrame,
    statement_dups: set,
    ledger_dups: set,
    snapshot: dict,
) -> pd.DataFrame:
    '''Build duplicate index table from both bases.'''
    rows: list = []
    for idx in sorted(statement_dups, key=str):
        rows.append(_duplicate_row(idx, None, 'statement', snapshot))
    for idx in sorted(ledger_dups, key=str):
        rows.append(_duplicate_row(None, idx, 'ledger', snapshot))
    if not rows:
        return _empty_frame()
    frame = pd.DataFrame(rows, columns=_MATCH_COLUMNS)
    return frame.sort_values(by=['source', 'statement_idx', 'ledger_idx']).reset_index(drop=True)


def _duplicate_row(first: object, second: object, source: str, snapshot: dict) -> dict:
    '''Build single duplicate row with deterministic id.'''
    marker = first if first is not None else second
    return {
        'statement_idx': first,
        'ledger_idx': second,
        'match_id': f'dup-{source}-{marker}',
        'day_diff': None,
        'value_diff': None,
        'description_score': None,
        'rule_id': 'RN-04',
        'reason': 'duplicada_suspeita',
        'params_snapshot': dict(snapshot),
        'source': source,
    }
