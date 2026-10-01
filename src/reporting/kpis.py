'''Kpi totals without streamlit.'''

from src.guards import safe_len as _shared_safe_len

_safe_len = _shared_safe_len


def calc_kpis(results: dict, statement_count: int = 0, ledger_count: int = 0) -> dict:
    '''Calculate totals and display percentages from result tables.'''
    auto_count = _safe_len(results.get('auto'))
    potential_count = _safe_len(results.get('potential'))
    pending_count = _safe_len(results.get('pending'))
    divergent_count = _safe_len(results.get('divergent'))
    duplicate_count = _safe_len(results.get('duplicate'))
    unified = auto_count + potential_count + pending_count + divergent_count
    unified = unified + duplicate_count
    if unified == 0:
        return _empty_kpis(statement_count, ledger_count)
    pct_auto = round(auto_count / unified * 100, 1)
    pct_review = round(potential_count / unified * 100, 1)
    pct_pending = round(pending_count / unified * 100, 1)
    pct_divergent = round((divergent_count + duplicate_count) / unified * 100, 1)
    return {
        'total_statement': int(statement_count),
        'total_ledger': int(ledger_count),
        'pct_auto': float(pct_auto),
        'pct_review': float(pct_review),
        'pct_pending': float(pct_pending),
        'pct_divergent': float(pct_divergent),
        'exception_rate': float(round(100.0 - pct_auto, 1)),
    }


def _empty_kpis(statement_count: int, ledger_count: int) -> dict:
    '''Build zeroed kpi dict.'''
    return {
        'total_statement': int(statement_count),
        'total_ledger': int(ledger_count),
        'pct_auto': 0.0,
        'pct_review': 0.0,
        'pct_pending': 0.0,
        'pct_divergent': 0.0,
        'exception_rate': 100.0,
    }
