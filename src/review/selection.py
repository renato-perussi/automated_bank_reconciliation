'''Visible frame selection honoring manual sets.'''

import pandas as pd


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
