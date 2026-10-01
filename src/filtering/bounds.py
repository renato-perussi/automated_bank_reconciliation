'''Slider bounds for display values.'''

import pandas as pd

from src.config import DEFAULT_SLIDER_HIGH, DEFAULT_SLIDER_LOW
from src.filtering.values import parse_amount_number


def _default_bounds() -> tuple:
    '''Return fallback display slider bounds.'''
    return (DEFAULT_SLIDER_LOW, DEFAULT_SLIDER_HIGH)


def _collect_display_values(display: pd.DataFrame) -> list:
    '''Collect numeric values from display amount columns.'''
    values: list = []
    for field in ['Valor', 'Valor extrato', 'Valor interno']:
        if field in display.columns:
            parsed = display[field].map(parse_amount_number)
            numeric = pd.to_numeric(parsed, errors='coerce').dropna()
            values.extend(numeric.tolist())
    return values


def value_bounds(display: pd.DataFrame) -> tuple:
    '''Infer display slider bounds from display values.'''
    if display is None:
        return _default_bounds()
    try:
        if len(display) == 0:
            return _default_bounds()
        values = _collect_display_values(display)
        if not values:
            return _default_bounds()
        low = float(min(values))
        high = float(max(values))
        if low == high:
            high = low + 1.0
        return (low, high)
    except (ValueError, TypeError):
        return _default_bounds()


def pending_bounds(left: pd.DataFrame, right: pd.DataFrame) -> tuple:
    '''Combine pending sides for slider bounds.'''
    if left is None or len(left) == 0:
        return value_bounds(right)
    if right is None or len(right) == 0:
        return value_bounds(left)
    try:
        combined = pd.concat([left, right], ignore_index=True)
    except (ValueError, TypeError):
        return value_bounds(left)
    return value_bounds(combined)
