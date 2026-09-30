'''Ambiguity resolution with deterministic tie breaker.'''

from decimal import Decimal

from src.classification.rules import _as_decimal


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
