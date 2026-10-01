'''Single candidate status rules RN-01 RN-02 RN-04 RN-05 RN-06 RN-07 RN-08.'''

from decimal import Decimal, InvalidOperation

from src.config import (
    DATE_TOLERANCE_DAYS,
    FUZZY_THRESHOLD,
    LOW_DESCRIPTION_SCORE,
    VALUE_TOLERANCE,
)
from src.logger import get_logger
from src.params import params_snapshot as _shared_snapshot

logger = get_logger(__name__)

_params_snapshot = _shared_snapshot


def _as_decimal(value: object) -> Decimal:
    '''Convert numeric input to Decimal safely.'''
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def _extract_fields(candidate: object) -> tuple:
    '''Extract day value score handling dict tuple forms.'''
    if isinstance(candidate, dict):
        return (
            candidate.get('day_diff'),
            candidate.get('value_diff'),
            candidate.get('description_score'),
        )
    values = list(candidate)
    day = values[2] if len(values) > 2 else None
    diff = values[3] if len(values) > 3 else None
    score = values[4] if len(values) > 4 else None
    return day, diff, score


def classify_match(
    candidate: object, params: dict, has_ambiguity: bool = False, is_duplicate: bool = False
) -> dict:
    '''Classify single candidate into status rule reason.'''
    if is_duplicate:
        return {'status': 'duplicate', 'rule_id': 'RN-04', 'reason': 'duplicada_suspeita'}
    if candidate is None:
        return {'status': 'pending', 'rule_id': 'RN-01', 'reason': 'sem_candidato'}
    day_diff, value_diff, score = _extract_fields(candidate)
    date_limit = params.get('date_tolerance_days', DATE_TOLERANCE_DAYS)
    if day_diff is None or day_diff > date_limit:
        return {'status': 'pending', 'rule_id': 'RN-02', 'reason': 'data_fora_tolerancia'}
    tolerance = params.get('value_tolerance', VALUE_TOLERANCE)
    try:
        diff_dec = _as_decimal(value_diff)
        tol_dec = _as_decimal(tolerance)
    except (InvalidOperation, ValueError, TypeError, AttributeError):
        logger.warning('Valor inválido na classificação.')
        return {'status': 'pending', 'rule_id': 'RN-08', 'reason': 'valor_fora_tolerancia'}
    if diff_dec > tol_dec:
        return {'status': 'pending', 'rule_id': 'RN-08', 'reason': 'valor_fora_tolerancia'}
    if has_ambiguity:
        return {'status': 'potential', 'rule_id': 'RN-07', 'reason': 'ambiguidade_multipla'}
    return _decide_value_fuzzy(diff_dec, score, params)


def _decide_value_fuzzy(diff_dec: Decimal, score: object, params: dict) -> dict:
    '''Decide cents versus exact paths deterministically.'''
    use_fuzzy = params.get('use_fuzzy', True)
    threshold = params.get('fuzzy_threshold', FUZZY_THRESHOLD)
    clean_score = 0 if score is None else int(score)
    if diff_dec != Decimal('0'):
        return _decide_cents(clean_score, use_fuzzy)
    return _decide_exact(clean_score, use_fuzzy, threshold)


def _decide_cents(score: int, use_fuzzy: bool) -> dict:
    '''Classify value divergent inside tolerance.'''
    if use_fuzzy and score < LOW_DESCRIPTION_SCORE:
        return {'status': 'divergent', 'rule_id': 'RN-08', 'reason': 'divergencia_valor_descricao'}
    return {'status': 'potential', 'rule_id': 'RN-08', 'reason': 'divergencia_centavos'}


def _decide_exact(score: int, use_fuzzy: bool, threshold: int) -> dict:
    '''Classify exact value by fuzzy threshold.'''
    if not use_fuzzy:
        return {'status': 'auto', 'rule_id': 'RN-06', 'reason': 'regra_composta_ok'}
    if score >= threshold:
        return {'status': 'auto', 'rule_id': 'RN-06', 'reason': 'regra_composta_ok'}
    if score >= LOW_DESCRIPTION_SCORE:
        return {'status': 'potential', 'rule_id': 'RN-05', 'reason': 'descricao_baixa_similaridade'}
    return {'status': 'divergent', 'rule_id': 'RN-05', 'reason': 'descricao_divergente'}
