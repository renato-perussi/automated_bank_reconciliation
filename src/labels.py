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

_REASON_SHORT_PT = {
    'regra_composta_ok': 'Confere',
    'descricao_baixa_similaridade': 'Baixa similaridade',
    'descricao_divergente': 'Descrição divergente',
    'divergencia_centavos': 'Centavos',
    'divergencia_valor_descricao': 'Valor e descrição',
    'ambiguidade_multipla': 'Múltiplos candidatos',
    'sem_candidato': 'Sem candidato',
    'data_fora_tolerancia': 'Data fora da tolerância',
    'valor_fora_tolerancia': 'Valor fora da tolerância',
    'sinal_bloqueado': 'Sinal oposto',
    'duplicada_suspeita': 'Duplicada suspeita',
}

_REASON_SHORT_BY_LABEL = {long: _REASON_SHORT_PT[code] for code, long in _REASON_PT.items()}


def status_label(category: object) -> str:
    '''Map internal category to pt-BR status.'''
    return STATUS_LABEL_PT.get(str(category), str(category))


def reason_label(raw: object) -> str:
    '''Translate internal motive code to pt-BR text.'''
    return _REASON_PT.get(str(raw), str(raw))


def reason_short(raw: object) -> str:
    '''Map reason code or long label to short badge text.'''
    if raw is None:
        return '—'
    text = str(raw).strip()
    if text == '' or text.lower() in ('nan', 'nat', 'none', '—', '<na>'):
        return '—'
    if text in _REASON_SHORT_PT:
        return _REASON_SHORT_PT[text]
    return _REASON_SHORT_BY_LABEL.get(text, text)


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
