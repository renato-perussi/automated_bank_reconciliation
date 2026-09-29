'''Classifier with five states ambiguity and duplicates.'''

from bisect import bisect_left, bisect_right
from decimal import Decimal

import pandas as pd

from src.config import APP_VERSION, DATE_TOLERANCE_DAYS, FUZZY_THRESHOLD, VALUE_TOLERANCE
from src.logger import get_logger
from src.matcher import find_candidates

logger = get_logger(__name__)

STATUS_LABEL_PT = {
    'auto': 'Conciliada',
    'potential': 'Para revisão',
    'pending': 'Pendente',
    'divergent': 'Divergente',
    'duplicate': 'Duplicada',
}

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


def _params_snapshot(params: dict) -> dict:
    '''Build deterministic snapshot with app version.'''
    return {
        'date_tolerance_days': params.get('date_tolerance_days', DATE_TOLERANCE_DAYS),
        'fuzzy_threshold': params.get('fuzzy_threshold', FUZZY_THRESHOLD),
        'value_tolerance': params.get('value_tolerance', VALUE_TOLERANCE),
        'use_fuzzy': params.get('use_fuzzy', True),
        'app_version': APP_VERSION,
    }


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


def _as_decimal(value: object) -> Decimal:
    '''Convert numeric input to Decimal safely.'''
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def _extract_fields(candidate: object) -> tuple:
    '''Extract day value score handling dict tuple forms.'''
    if isinstance(candidate, dict):
        return (
            candidate.get('day_diff'),
            candidate.get('value_diff'),
            candidate.get('description_score'),
        )
    values = list(candidate)
    day = values[2] if len(values) > 2 else None
    diff = values[3] if len(values) > 3 else None
    score = values[4] if len(values) > 4 else None
    return day, diff, score


def classify_match(
    candidate: object, params: dict, has_ambiguity: bool = False, is_duplicate: bool = False
) -> dict:
    '''Classify single candidate into status rule reason.'''
    if is_duplicate:
        return {'status': 'duplicate', 'rule_id': 'RN-04', 'reason': 'duplicada_suspeita'}
    if candidate is None:
        return {'status': 'pending', 'rule_id': 'RN-01', 'reason': 'sem_candidato'}
    day_diff, value_diff, score = _extract_fields(candidate)
    date_limit = params.get('date_tolerance_days', DATE_TOLERANCE_DAYS)
    if day_diff is None or day_diff > date_limit:
        return {'status': 'pending', 'rule_id': 'RN-02', 'reason': 'data_fora_tolerancia'}
    tolerance = params.get('value_tolerance', VALUE_TOLERANCE)
    try:
        diff_dec = _as_decimal(value_diff)
        tol_dec = _as_decimal(tolerance)
    except Exception:
        logger.warning('Valor inválido na classificação.')
        return {'status': 'pending', 'rule_id': 'RN-08', 'reason': 'valor_fora_tolerancia'}
    if diff_dec > tol_dec:
        return {'status': 'pending', 'rule_id': 'RN-08', 'reason': 'valor_fora_tolerancia'}
    if has_ambiguity:
        return {'status': 'potential', 'rule_id': 'RN-07', 'reason': 'ambiguidade_multipla'}
    return _decide_value_fuzzy(diff_dec, score, params)


def _decide_value_fuzzy(diff_dec: Decimal, score: object, params: dict) -> dict:
    '''Decide cents versus exact paths deterministically.'''
    use_fuzzy = params.get('use_fuzzy', True)
    threshold = params.get('fuzzy_threshold', FUZZY_THRESHOLD)
    clean_score = 0 if score is None else int(score)
    if diff_dec != Decimal('0'):
        return _decide_cents(clean_score, use_fuzzy)
    return _decide_exact(clean_score, use_fuzzy, threshold)


def _decide_cents(score: int, use_fuzzy: bool) -> dict:
    '''Classify value divergent inside tolerance.'''
    if use_fuzzy and score < 60:
        return {'status': 'divergent', 'rule_id': 'RN-08', 'reason': 'divergencia_valor_descricao'}
    return {'status': 'potential', 'rule_id': 'RN-08', 'reason': 'divergencia_centavos'}


def _decide_exact(score: int, use_fuzzy: bool, threshold: int) -> dict:
    '''Classify exact value by fuzzy threshold.'''
    if not use_fuzzy:
        return {'status': 'auto', 'rule_id': 'RN-06', 'reason': 'regra_composta_ok'}
    if score >= threshold:
        return {'status': 'auto', 'rule_id': 'RN-06', 'reason': 'regra_composta_ok'}
    if score >= 60:
        return {'status': 'potential', 'rule_id': 'RN-05', 'reason': 'descricao_baixa_similaridade'}
    return {'status': 'divergent', 'rule_id': 'RN-05', 'reason': 'descricao_divergente'}


def _group_by(candidates: list, field: str) -> dict:
    '''Group candidates by statement or ledger key.'''
    grouped: dict = {}
    for item in candidates:
        key = item.get(field)
        grouped.setdefault(key, []).append(item)
    return grouped


def _sort_key(item: dict) -> tuple:
    '''Build deterministic tie breaker for ambiguity.'''
    day = item.get('day_diff')
    if day is None:
        day = 9999
    score = item.get('description_score')
    if score is None:
        score = 0
    diff = item.get('value_diff')
    if diff is None:
        diff = Decimal('0')
    first = str(item.get('statement_idx'))
    second = str(item.get('ledger_idx'))
    return (int(day), -int(score), _as_decimal(diff), first, second)


def _pick_best(group: list) -> tuple:
    '''Pick best candidate preferring date then score.'''
    ordered = sorted(group, key=_sort_key)
    return ordered[0], ordered[1:]


def resolve_ambiguity(candidates: list) -> tuple:
    '''Resolve one to many choosing smallest day highest score.'''
    if not candidates:
        return ([], [])
    winners_stage: list = []
    losers: list = []
    for group in _group_by(candidates, 'statement_idx').values():
        if len(group) == 1:
            winners_stage.append(group[0])
            continue
        best, rest = _pick_best(group)
        winners_stage.append(best)
        losers.extend(rest)
    winners: list = []
    for group in _group_by(winners_stage, 'ledger_idx').values():
        if len(group) == 1:
            winners.append(group[0])
            continue
        best, rest = _pick_best(group)
        winners.append(best)
        losers.extend(rest)
    winners.sort(key=lambda item: (str(item.get('statement_idx')), str(item.get('ledger_idx'))))
    losers.sort(key=lambda item: (str(item.get('statement_idx')), str(item.get('ledger_idx'))))
    return (winners, losers)


def _count_links(candidates: list) -> tuple:
    '''Count candidates per statement and ledger keys.'''
    count_statement: dict = {}
    count_ledger: dict = {}
    for item in candidates:
        first = item.get('statement_idx')
        second = item.get('ledger_idx')
        count_statement[first] = count_statement.get(first, 0) + 1
        count_ledger[second] = count_ledger.get(second, 0) + 1
    return (count_statement, count_ledger)


def _build_match_id(first: object, second: object) -> str:
    '''Build deterministic pair identifier.'''
    return f's{first}-l{second}'


def _collect_simple_entries(frame: pd.DataFrame) -> list:
    '''Collect valid amount sign date entries for checks.'''
    entries: list = []
    for idx, row in frame.iterrows():
        code = row['error_code'] if 'error_code' in row.index else None
        if isinstance(code, str) and code.strip() != '':
            continue
        amount = _pick_amount(row)
        entry_date = _pick_date(row)
        sign = _pick_sign(row)
        if amount is None or entry_date is None or sign is None:
            continue
        entries.append({'entry_idx': idx, 'amount': amount, 'entry_date': entry_date, 'sign': sign})
    return entries


def _pick_amount(row: pd.Series) -> object:
    '''Pick first available normalized amount.'''
    for field in ('normalized_amount', 'normalized_value'):
        if field not in row.index:
            continue
        value = row[field]
        if value is None:
            continue
        try:
            if pd.isna(value):
                continue
        except (ValueError, TypeError):
            pass
        return value
    return None


def _pick_date(row: pd.Series) -> object:
    '''Pick normalized date when present.'''
    if 'normalized_date' not in row.index:
        return None
    value = row['normalized_date']
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except (ValueError, TypeError):
        pass
    return value


def _pick_sign(row: pd.Series) -> object:
    '''Pick integer sign when present.'''
    if 'sign' not in row.index:
        return None
    value = row['sign']
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except (ValueError, TypeError):
        pass
    try:
        return int(value)
    except (ValueError, TypeError):
        return None


def _build_amount_index(entries: list) -> tuple:
    '''Build sorted absolute amount index for signal check.'''
    ordered = sorted(entries, key=lambda item: abs(item['amount']))
    amounts = [abs(item['amount']) for item in ordered]
    return (amounts, ordered)


def _is_signal_blocked(
    target: dict, amounts: list, ordered: list, tolerance: Decimal, limit: int
) -> bool:
    '''Check opposite sign inside absolute amount date window.'''
    target_abs = abs(target['amount'])
    low = target_abs - tolerance
    high = target_abs + tolerance
    left = bisect_left(amounts, low)
    right = bisect_right(amounts, high)
    for other in ordered[left:right]:
        if other['sign'] == target['sign']:
            continue
        try:
            first_day = target['entry_date']
            second_day = other['entry_date']
            if hasattr(first_day, 'date') and callable(first_day.date):
                first_day = first_day.date()
            if hasattr(second_day, 'date') and callable(second_day.date):
                second_day = second_day.date()
            day_diff = abs((first_day - second_day).days)
        except (ValueError, TypeError, AttributeError):
            continue
        if day_diff <= limit:
            return True
    return False


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


def _resolve_pending_limits(params: dict) -> tuple:
    '''Resolve tolerance and date limit for pending checks.'''
    tolerance = params.get('value_tolerance', VALUE_TOLERANCE)
    limit = params.get('date_tolerance_days', DATE_TOLERANCE_DAYS)
    if not isinstance(tolerance, Decimal):
        tolerance = Decimal(str(tolerance))
    return (tolerance, limit)


def _collect_all_pending_rows(
    statement_df: pd.DataFrame,
    ledger_df: pd.DataFrame,
    params: dict,
    matched: tuple,
    statement_dups: set,
    ledger_dups: set,
    snapshot: dict,
) -> list:
    '''Collect pending rows from both bases with signal check.'''
    matched_statement, matched_ledger = matched
    statement_entries = _collect_simple_entries(statement_df)
    ledger_entries = _collect_simple_entries(ledger_df)
    statement_amounts, statement_ordered = _build_amount_index(statement_entries)
    ledger_amounts, ledger_ordered = _build_amount_index(ledger_entries)
    tolerance, limit = _resolve_pending_limits(params)
    rows = _pending_side(
        statement_entries, ledger_amounts, ledger_ordered, matched_statement, statement_dups,
        snapshot, tolerance, limit, 'statement',
    )
    rows.extend(
        _pending_side(
            ledger_entries, statement_amounts, statement_ordered, matched_ledger, ledger_dups,
            snapshot, tolerance, limit, 'ledger',
        )
    )
    return rows


def _pending_side(
    entries: list,
    other_amounts: list,
    other_ordered: list,
    matched_side: set,
    dups: set,
    snapshot: dict,
    tolerance: Decimal,
    limit: int,
    source: str,
) -> list:
    '''Collect pending rows for single side.'''
    return _pending_rows(
        entries, other_amounts, other_ordered, matched_side, dups, source, tolerance, limit,
        snapshot,
    )


def _build_pending_table(
    statement_df: pd.DataFrame,
    ledger_df: pd.DataFrame,
    params: dict,
    matched: tuple,
    statement_dups: set,
    ledger_dups: set,
    snapshot: dict,
) -> pd.DataFrame:
    '''Build pending table for unmatched valid rows.'''
    rows = _collect_all_pending_rows(
        statement_df, ledger_df, params, matched, statement_dups, ledger_dups, snapshot
    )
    if not rows:
        return _empty_frame()
    frame = pd.DataFrame(rows, columns=_MATCH_COLUMNS)
    return frame.sort_values(by=['source', 'statement_idx', 'ledger_idx']).reset_index(drop=True)


def _pending_rows(
    entries: list,
    other_amounts: list,
    other_ordered: list,
    matched_side: set,
    dups: set,
    source: str,
    tolerance: Decimal,
    limit: int,
    snapshot: dict,
) -> list:
    '''Build pending rows detecting signal blocked motive.'''
    rows: list = []
    for entry in entries:
        idx = entry['entry_idx']
        if idx in matched_side or idx in dups:
            continue
        if _is_signal_blocked(entry, other_amounts, other_ordered, tolerance, limit):
            rule = 'RN-03'
            reason = 'sinal_bloqueado'
        else:
            rule = 'RN-01'
            reason = 'sem_candidato'
        rows.append(_pending_row(idx, source, rule, reason, snapshot))
    return rows


def _pending_row(idx: object, source: str, rule: str, reason: str, snapshot: dict) -> dict:
    '''Build single pending row with empty match fields.'''
    if source == 'statement':
        first, second = idx, None
    else:
        first, second = None, idx
    return {
        'statement_idx': first,
        'ledger_idx': second,
        'match_id': None,
        'day_diff': None,
        'value_diff': None,
        'description_score': None,
        'rule_id': rule,
        'reason': reason,
        'params_snapshot': dict(snapshot),
        'source': source,
    }


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
    statement_dups = detect_duplicates(statement_df, params)
    ledger_dups = detect_duplicates(ledger_df, params)
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
