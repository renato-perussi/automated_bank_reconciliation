'''Counters and ratios for display.'''


def safe_ratio(pct: float) -> float:
    '''Convert display percentage to display progress ratio.'''
    try:
        ratio = float(pct) / 100.0
    except (ValueError, TypeError):
        return 0.0
    if ratio < 0.0:
        return 0.0
    if ratio > 1.0:
        return 1.0
    return ratio


def format_match_counter(shown: int, total: int) -> str:
    '''Format single tab counter in pt-BR slash style.'''
    return f'Mostrando {int(shown)}/{int(total)}'


def format_pending_counter(
    left_shown: int, right_shown: int, left_total: int, right_total: int
) -> str:
    '''Format pending counter in pt-BR slash style.'''
    left = f'{int(left_shown)}/{int(left_total)}'
    right = f'{int(right_shown)}/{int(right_total)}'
    return f'Mostrando {left} e {right}'
