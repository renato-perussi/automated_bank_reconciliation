'''Shared pt-BR status reason manual labels.'''

STATUS_LABEL_PT = {
    'auto': 'Conciliada',
    'potential': 'Para revisão',
    'pending': 'Pendente',
    'divergent': 'Divergente',
    'duplicate': 'Duplicada',
}

_REASON_PT = {
    'regra_composta_ok': 'Valor, data e descrição conferem',
    'descricao_baixa_similaridade': 'Descrição com baixa similaridade',
    'descricao_divergente': 'Descrição divergente',
    'divergencia_centavos': 'Divergência de centavos',
    'divergencia_valor_descricao': 'Valor e descrição divergentes',
    'ambiguidade_multipla': 'Múltiplos candidatos possíveis',
    'sem_candidato': 'Sem candidato próximo',
    'data_fora_tolerancia': 'Data fora da tolerância',
    'valor_fora_tolerancia': 'Valor fora da tolerância',
    'sinal_bloqueado': 'Sinal oposto (débito x crédito)',
    'duplicada_suspeita': 'Duplicada suspeita',
}


def status_label(category: object) -> str:
    '''Map internal category to pt-BR status.'''
    return STATUS_LABEL_PT.get(str(category), str(category))


def reason_label(raw: object) -> str:
    '''Translate internal motive code to pt-BR text.'''
    return _REASON_PT.get(str(raw), str(raw))


def manual_label(action: object) -> str:
    '''Translate review action to pt-BR label.'''
    text = str(action) if action is not None else ''
    if text == 'conciliada_manual':
        return 'Confirmada manualmente'
    if text == 'rejeitada':
        return 'Rejeitada'
    if text == 'Confirmada manualmente':
        return text
    if text == 'Rejeitada':
        return text
    return ''


def manual_lookup(review_log: object) -> dict:
    '''Index manual decisions by match id keeping last.'''
    lookup: dict = {}
    if not isinstance(review_log, list):
        return lookup
    for entry in review_log:
        if not isinstance(entry, dict):
            continue
        pair = entry.get('match_id')
        if pair is None:
            continue
        lookup[str(pair)] = {
            'review_action': entry.get('review_action', ''),
            'timestamp': entry.get('timestamp', ''),
        }
    return lookup
