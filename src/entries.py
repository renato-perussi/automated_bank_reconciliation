'''Shared entry collection and amount indexing.'''

from bisect import bisect_left, bisect_right
from decimal import Decimal

from src.guards import calc_day_diff, has_error_code, is_missing


def resolve_amount(row: object) -> object:
    '''Resolve Decimal amount preferring amount field.'''
    for field in ('normalized_amount', 'normalized_value'):
        try:
            if field not in row.index:
                continue
            value = row[field]
        except (AttributeError, KeyError, TypeError):
            continue
        if value is None or is_missing(value):
            continue
        return value
    return None


def resolve_entry_date(row: object) -> object:
    '''Resolve normalized date or none when missing.'''
    try:
        if 'normalized_date' not in row.index:
            return None
        value = row['normalized_date']
    except (AttributeError, KeyError, TypeError):
        return None
    if value is None or is_missing(value):
        return None
    return value


def resolve_entry_text(row: object) -> str:
    '''Resolve normalized description or empty string.'''
    try:
        if 'normalized_description' not in row.index:
            return ''
        value = row['normalized_description']
    except (AttributeError, KeyError, TypeError):
        return ''
    if value is None:
        return ''
    if is_missing(value):
        return ''
    return str(value)


def resolve_entry_sign(row: object) -> object:
    '''Resolve integer sign or none when missing.'''
    try:
        if 'sign' not in row.index:
            return None
        value = row['sign']
    except (AttributeError, KeyError, TypeError):
        return None
    if value is None or is_missing(value):
        return None
    try:
        return int(value)
    except (ValueError, TypeError):
        return None


def collect_entries(frame: object) -> list:
    '''Collect valid entries with amount sign date text.'''
    entries: list = []
    try:
        iterator = frame.iterrows()
    except AttributeError:
        return entries
    for idx, row in iterator:
        if has_error_code(row):
            continue
        amount = resolve_amount(row)
        entry_date = resolve_entry_date(row)
        sign = resolve_entry_sign(row)
        if amount is None or entry_date is None or sign is None:
            continue
        if is_missing(amount) or is_missing(entry_date):
            continue
        entries.append(
            {
                'entry_idx': idx,
                'amount': amount,
                'entry_date': entry_date,
                'sign': sign,
                'entry_text': resolve_entry_text(row),
            }
        )
    return entries


def build_ledger_index(entries: list) -> dict:
    '''Build sign grouped sorted index for range lookup.'''
    grouped: dict = {}
    for entry in entries:
        grouped.setdefault(entry['sign'], []).append(entry)
    index: dict = {}
    for sign, items in grouped.items():
        ordered = sorted(items, key=lambda item: item['amount'])
        amounts = [item['amount'] for item in ordered]
        index[sign] = {'amounts': amounts, 'items': ordered}
    return index


def find_amount_window(amounts: list, items: list, target: object, tolerance: Decimal) -> list:
    '''Find indexed items inside amount tolerance window.'''
    low = target - tolerance
    high = target + tolerance
    left = bisect_left(amounts, low)
    right = bisect_right(amounts, high)
    return items[left:right]


def build_amount_index(entries: list) -> tuple:
    '''Build sorted absolute amount index for signal check.'''
    ordered = sorted(entries, key=lambda item: abs(item['amount']))
    amounts = [abs(item['amount']) for item in ordered]
    return (amounts, ordered)


def is_signal_blocked(
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
            day_diff = calc_day_diff(target['entry_date'], other['entry_date'])
        except (ValueError, TypeError, AttributeError):
            continue
        if day_diff <= limit:
            return True
    return False
