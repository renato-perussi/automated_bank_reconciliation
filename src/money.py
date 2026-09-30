'''Shared Decimal money helpers without float.'''

from decimal import Decimal, InvalidOperation

from src.guards import is_missing


def to_decimal(value: object) -> Decimal:
    '''Convert supported numeric input to Decimal.'''
    if isinstance(value, Decimal):
        return value
    if isinstance(value, bool):
        raise ValueError('Tolerância de valor deve ser maior ou igual a 0.')
    if isinstance(value, int):
        return Decimal(value)
    return Decimal(str(value))


def calc_value_diff(first: object, second: object) -> Decimal:
    '''Calculate absolute Decimal difference without float.'''
    return abs(to_decimal(first) - to_decimal(second))


def convert_tolerance(value: object) -> Decimal:
    '''Convert tolerance input preserving exactness.'''
    if isinstance(value, Decimal):
        return value
    if isinstance(value, int):
        return Decimal(value)
    if isinstance(value, float):
        return Decimal(str(value))
    return Decimal(str(value))


def ensure_value_tolerance(value: object) -> Decimal:
    '''Validate and convert value tolerance to Decimal.'''
    if isinstance(value, bool):
        raise ValueError('Tolerância de valor deve ser maior ou igual a 0.')
    try:
        clean = convert_tolerance(value)
    except (InvalidOperation, ValueError, TypeError, AttributeError):
        raise ValueError('Tolerância de valor deve ser maior ou igual a 0.')
    if clean < Decimal('0'):
        raise ValueError('Tolerância de valor deve ser maior ou igual a 0.')
    return clean


def as_number(value: object) -> object:
    '''Convert Decimal numeric to float preserving none.'''
    if value is None:
        return None
    if is_missing(value):
        return None
    if isinstance(value, bool):
        return None
    try:
        return float(Decimal(str(value)))
    except (InvalidOperation, ValueError, TypeError):
        return None


def format_brl(raw_value: object) -> str:
    '''Format numeric input as pt-BR currency text.'''
    if raw_value is None:
        return '—'
    if is_missing(raw_value):
        return '—'
    try:
        amount = Decimal(str(raw_value))
    except (InvalidOperation, ValueError, TypeError):
        return str(raw_value)
    quantized = amount.quantize(Decimal('0.00'))
    text = f'{quantized:,.2f}'
    text = text.replace(',', 'X').replace('.', ',').replace('X', '.')
    return f'R$ {text}'
