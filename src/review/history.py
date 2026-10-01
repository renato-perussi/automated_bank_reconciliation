'''Review history display helpers.'''

from datetime import datetime

import pandas as pd

from src.labels import manual_label as _shared_manual_label


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
