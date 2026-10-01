'''Manual review state transitions.'''

from datetime import datetime


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
