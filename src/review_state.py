'''Pure manual review transitions without streamlit.'''

from datetime import datetime

import pandas as pd

from src.labels import manual_label as _shared_manual_label


def ensure_review_keys(state: dict) -> dict:
    '''Ensure review keys inside plain state dict.'''
    if 'review_log' not in state:
        state['review_log'] = []
    if 'manual_confirmed' not in state:
        state['manual_confirmed'] = set()
    if 'manual_rejected' not in state:
        state['manual_rejected'] = set()
    if 'feedback' not in state:
        state['feedback'] = None
    return state


def confirm_pair_state(state: dict, pair_id: str, timestamp: object = None) -> dict:
    '''Mark pair manual moving to conciliadas.'''
    ensure_review_keys(state)
    confirmed = set(state.get('manual_confirmed', set()))
    rejected = set(state.get('manual_rejected', set()))
    confirmed.add(str(pair_id))
    rejected.discard(str(pair_id))
    state['manual_confirmed'] = confirmed
    state['manual_rejected'] = rejected
    moment = str(timestamp) if timestamp is not None else datetime.now().isoformat()
    log_items = list(state.get('review_log', []))
    log_items.append(
        {'match_id': str(pair_id), 'review_action': 'conciliada_manual', 'timestamp': moment}
    )
    state['review_log'] = log_items
    state['feedback'] = 'Par confirmado manualmente.'
    return state


def reject_pair_state(state: dict, pair_id: str, timestamp: object = None) -> dict:
    '''Reject pair returning to pendente pool.'''
    ensure_review_keys(state)
    confirmed = set(state.get('manual_confirmed', set()))
    rejected = set(state.get('manual_rejected', set()))
    rejected.add(str(pair_id))
    confirmed.discard(str(pair_id))
    state['manual_confirmed'] = confirmed
    state['manual_rejected'] = rejected
    moment = str(timestamp) if timestamp is not None else datetime.now().isoformat()
    log_items = list(state.get('review_log', []))
    log_items.append(
        {'match_id': str(pair_id), 'review_action': 'rejeitada', 'timestamp': moment}
    )
    state['review_log'] = log_items
    state['feedback'] = 'Par rejeitado e devolvido para pendente.'
    return state


def undo_last_review_state(state: dict) -> object:
    '''Revert last manual decision in plain state.'''
    log_items = list(state.get('review_log', []))
    if not log_items:
        return None
    last = log_items.pop()
    pair_id = last.get('match_id')
    confirmed = set(state.get('manual_confirmed', set()))
    rejected = set(state.get('manual_rejected', set()))
    confirmed.discard(pair_id)
    rejected.discard(pair_id)
    state['manual_confirmed'] = confirmed
    state['manual_rejected'] = rejected
    state['review_log'] = log_items
    state['feedback'] = 'Última ação desfeita.'
    return last


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


def history_label(action: object) -> str:
    '''Translate review action to pt-BR.'''
    label = _shared_manual_label(action)
    return label if label != '' else str(action)


def history_moment(raw: object) -> str:
    '''Format iso timestamp to pt-BR display.'''
    text = str(raw)
    try:
        moment = datetime.fromisoformat(text)
        return moment.strftime('%d/%m/%Y %H:%M:%S')
    except (ValueError, TypeError):
        return text


def history_display(log_items: list) -> pd.DataFrame:
    '''Build pt-BR history frame for display.'''
    rows: list = []
    for item in log_items:
        rows.append(
            {
                'Par ID': item.get('match_id'),
                'Ação': history_label(item.get('review_action')),
                'Data/Hora': history_moment(item.get('timestamp')),
            }
        )
    return pd.DataFrame(rows, columns=['Par ID', 'Ação', 'Data/Hora'])


def filtered_review_rows(potential: object, confirmed: set, rejected: set) -> object:
    '''Filter potential removing confirmed rejected pairs.'''
    blocked = set(confirmed) | set(rejected)
    if 'match_id' not in potential.columns:
        return potential
    return potential[~potential['match_id'].isin(blocked)]


def confirmed_rows(results: object, confirmed: set) -> pd.DataFrame:
    '''Collect confirmed rows from original potential table.'''
    if results is None or not confirmed:
        return pd.DataFrame()
    potential = results.get('potential')
    if potential is None or len(potential) == 0:
        return pd.DataFrame()
    return potential[potential['match_id'].isin(confirmed)]


def active_frame(
    match_frame: object, prefix: str, confirmed: set, rejected: set, results: object = None
) -> pd.DataFrame:
    '''Select visible rows honoring manual review sets.'''
    if match_frame is None:
        return pd.DataFrame()
    if prefix == 'auto':
        extra = confirmed_rows(results, confirmed)
        if len(extra) == 0:
            return match_frame
        return pd.concat([match_frame, extra], ignore_index=True)
    if prefix == 'potential':
        if 'match_id' not in match_frame.columns:
            return match_frame
        blocked = set(confirmed) | set(rejected)
        return match_frame[~match_frame['match_id'].isin(blocked)]
    return match_frame
