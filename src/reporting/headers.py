'''Report pt-BR headers and label wrappers.'''

from src.labels import STATUS_LABEL_PT as _shared_status_map
from src.labels import manual_label as _shared_manual_label
from src.labels import manual_lookup as _shared_manual_lookup
from src.labels import reason_label as _shared_reason_label
from src.labels import status_label as _shared_status_label

_REPORT_HEADERS = (
    'Origem',
    'Data original',
    'Data normalizada',
    'Descrição original',
    'Valor original',
    'Valor normalizado',
    'Sinal',
    'Status',
    'Par ID',
    'Diferença dias',
    'Diferença valor',
    'Score descrição',
    'Regra ID',
    'Motivo',
    'Ação manual',
)

_LOG_HEADERS_PT = (
    'Par ID',
    'Regra ID',
    'Diferença dias',
    'Diferença valor',
    'Score descrição',
    'Motivo',
    'Código erro',
    'Ação manual',
    'Data/Hora ação',
    'Parâmetros',
)

_ERROR_HEADERS_PT = ('Linha', 'Motivo', 'Como corrigir')

_STATUS_PT = dict(_shared_status_map)


def _manual_lookup(review_log: object) -> dict:
    '''Index manual decisions by match id keeping last.'''
    return _shared_manual_lookup(review_log)


def _manual_label(action: object) -> str:
    '''Translate review action to pt-BR label.'''
    return _shared_manual_label(action)


def _status_label(category: str) -> str:
    '''Map internal category to pt-BR status.'''
    return _shared_status_label(category)


def _reason_label(raw: object) -> str:
    '''Translate internal motive code to pt-BR text.'''
    return _shared_reason_label(raw)
