'''Description canonical form.'''

import re
import unicodedata

import pandas as pd


def normalize_description(raw: object) -> str:
    '''Normalize description to canonical comparable form.'''
    if raw is None:
        return ''
    try:
        if pd.isna(raw):
            return ''
    except (ValueError, TypeError):
        pass
    text = str(raw).lower().strip()
    if text == '':
        return ''
    folded = unicodedata.normalize('NFKD', text)
    stripped = ''.join([c for c in folded if not unicodedata.combining(c)])
    cleaned = re.sub(r'[^a-z0-9\s]', '', stripped)
    return ' '.join(cleaned.split())
