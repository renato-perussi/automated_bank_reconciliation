'''Shared fixtures for tests.'''

from decimal import Decimal
from pathlib import Path

import pytest


@pytest.fixture
def sample_config() -> dict:
    '''Provide default engine parameters for tests.'''
    return {
        'date_tolerance_days': 2,
        'fuzzy_threshold': 85,
        'value_tolerance': Decimal('0.00'),
    }


@pytest.fixture
def fixture_paths() -> dict:
    '''Provide stable paths to pt-BR fixtures.'''
    base = Path(__file__).parent / 'fixtures'
    return {
        'statement': base / 'extrato.csv',
        'ledger': base / 'interno.xlsx',
        'duplicates': base / 'duplicadas.csv',
        'matrix': base / 'matrix',
    }
