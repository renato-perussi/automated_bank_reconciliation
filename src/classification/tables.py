'''Five table assembly from classified rows.'''

import pandas as pd

from src.classification.ambiguity import _build_match_id, _count_links, resolve_ambiguity
from src.classification.duplicates import _MATCH_COLUMNS, _build_duplicate_table, _empty_frame
from src.classification.duplicates import detect_duplicates as _detect_dups
from src.classification.pending import _build_pending_table
from src.classification.rules import _params_snapshot, classify_match
from src.logger import get_logger
from src.matcher import find_candidates

logger = get_logger(__name__)


def _classify_single(
    item: dict, counts: tuple, dups: tuple, params: dict, snapshot: dict
) -> tuple:
    '''Classify one candidate returning row status matched pair.'''
    count_statement, count_ledger = counts
    statement_dups, ledger_dups = dups
    first = item.get('statement_idx')
    second = item.get('ledger_idx')
    ambiguous = count_statement.get(first, 0) > 1 or count_ledger.get(second, 0) > 1
    duplicated = first in statement_dups or second in ledger_dups
    result = classify_match(item, params, ambiguous, duplicated)
    status = result.get('status')
    if status == 'duplicate':
        return (None, status, first, second)
    row = _match_row(item, result, snapshot)
    return (row, status, first, second)


def _classify_all(
    winners: list, losers: list, counts: tuple, dups: tuple, params: dict, snapshot: dict
) -> tuple:
    '''Classify winners losers into auto potential divergent.'''
    auto_rows: list = []
    potential_rows: list = []
    divergent_rows: list = []
    matched_statement: set = set()
    matched_ledger: set = set()
    for item in winners + losers:
        row, status, first, second = _classify_single(item, counts, dups, params, snapshot)
        matched_statement.add(first)
        matched_ledger.add(second)
        if row is None:
            continue
        if status == 'auto':
            auto_rows.append(row)
        elif status == 'divergent':
            divergent_rows.append(row)
        elif status == 'potential':
            potential_rows.append(row)
    return (auto_rows, potential_rows, divergent_rows, (matched_statement, matched_ledger))


def _match_row(item: dict, result: dict, snapshot: dict) -> dict:
    '''Build match row with identifiers and audit fields.'''
    first = item.get('statement_idx')
    second = item.get('ledger_idx')
    return {
        'statement_idx': first,
        'ledger_idx': second,
        'match_id': _build_match_id(first, second),
        'day_diff': item.get('day_diff'),
        'value_diff': item.get('value_diff'),
        'description_score': item.get('description_score'),
        'rule_id': result.get('rule_id'),
        'reason': result.get('reason'),
        'params_snapshot': dict(snapshot),
        'source': 'matched',
    }


def _frame_from_rows(rows: list) -> pd.DataFrame:
    '''Build sorted match frame from row dicts.'''
    if not rows:
        return _empty_frame()
    frame = pd.DataFrame(rows, columns=_MATCH_COLUMNS)
    return frame.sort_values(by=['statement_idx', 'ledger_idx']).reset_index(drop=True)


def _include_dups(matched: tuple, statement_dups: set, ledger_dups: set) -> None:
    '''Include duplicate indices into matched sets.'''
    matched_statement, matched_ledger = matched
    matched_statement.update(statement_dups)
    matched_ledger.update(ledger_dups)


def _assemble_tables(
    auto_rows: list,
    potential_rows: list,
    divergent_rows: list,
    statement_df: pd.DataFrame,
    ledger_df: pd.DataFrame,
    params: dict,
    matched: tuple,
    statement_dups: set,
    ledger_dups: set,
    snapshot: dict,
) -> dict:
    '''Assemble five sorted tables from classified rows.'''
    _include_dups(matched, statement_dups, ledger_dups)
    auto = _frame_from_rows(auto_rows)
    potential = _frame_from_rows(potential_rows)
    divergent = _frame_from_rows(divergent_rows)
    duplicate = _build_duplicate_table(
        statement_df, ledger_df, statement_dups, ledger_dups, snapshot
    )
    pending = _build_pending_table(
        statement_df, ledger_df, params, matched, statement_dups, ledger_dups, snapshot
    )
    return {
        'auto': auto,
        'potential': potential,
        'pending': pending,
        'divergent': divergent,
        'duplicate': duplicate,
    }


def build_result_tables(
    statement_df: pd.DataFrame, ledger_df: pd.DataFrame, params: dict
) -> dict:
    '''Run full pipeline returning five auditable tables.'''
    snapshot = _params_snapshot(params)
    candidates = find_candidates(statement_df, ledger_df, params)
    statement_dups = _detect_dups(statement_df, params)
    ledger_dups = _detect_dups(ledger_df, params)
    winners, losers = resolve_ambiguity(candidates)
    counts = _count_links(candidates)
    auto_rows, potential_rows, divergent_rows, matched = _classify_all(
        winners, losers, counts, (statement_dups, ledger_dups), params, snapshot
    )
    tables = _assemble_tables(
        auto_rows,
        potential_rows,
        divergent_rows,
        statement_df,
        ledger_df,
        params,
        matched,
        statement_dups,
        ledger_dups,
        snapshot,
    )
    logger.info('Built tables auto potential pending divergent duplicate.')
    return tables
