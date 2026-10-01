'''Adjusted counts and kpi overlay.'''


def adjusted_counts(results: object, confirmed: set, rejected: set) -> tuple:
    '''Compute effective auto potential after manual review.'''
    if results is None:
        return (0, 0, 0, 0, 0, 0, 0)
    auto_len = len(results.get('auto')) + len(confirmed)
    pot_len = len(results.get('potential')) - len(confirmed) - len(rejected)
    pot_len = pot_len if pot_len >= 0 else 0
    pending_len = len(results.get('pending')) + len(rejected)
    divergent_len = len(results.get('divergent'))
    duplicate_len = len(results.get('duplicate'))
    unified = auto_len + pot_len + pending_len + divergent_len + duplicate_len
    return (auto_len, pot_len, pending_len, divergent_len, duplicate_len, unified, len(confirmed))


def apply_manual_kpis(kpis: dict, counts: tuple) -> dict:
    '''Adjust percentages for confirmed rejected pairs.'''
    auto_len, pot_len, pending_len, divergent_len, dup_len, unified, _ = counts
    if unified == 0:
        return kpis
    pct_auto = round(auto_len / unified * 100, 1)
    pct_review = round(pot_len / unified * 100, 1)
    pending_div = pending_len + divergent_len + dup_len
    pct_pending = round(pending_div / unified * 100, 1) if unified else 0.0
    pct_divergent = round((divergent_len + dup_len) / unified * 100, 1)
    updated = dict(kpis)
    updated['pct_auto'] = float(pct_auto)
    updated['pct_review'] = float(pct_review)
    updated['pct_pending'] = float(pct_pending)
    updated['pct_divergent'] = float(pct_divergent)
    updated['exception_rate'] = round(100.0 - pct_auto, 1)
    return updated
