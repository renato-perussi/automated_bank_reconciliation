'''Default config checks.'''

from decimal import Decimal

import src.config as config


def test_date_tolerance_default() -> None:
    '''Ensure date window matches PRD default.'''
    assert config.DATE_TOLERANCE_DAYS == 2


def test_fuzzy_threshold_default() -> None:
    '''Ensure fuzzy threshold matches PRD default.'''
    assert config.FUZZY_THRESHOLD == 85


def test_value_tolerance_default() -> None:
    '''Ensure exact value match by default.'''
    assert config.VALUE_TOLERANCE == Decimal('0.00')


def test_file_limits() -> None:
    '''Ensure local execution limits stay safe.'''
    assert config.MAX_FILE_SIZE_MB == 20
    assert config.MAX_ROWS_WARNING == 20000


def test_supported_extensions() -> None:
    '''Ensure only CSV and Excel are accepted.'''
    assert config.SUPPORTED_EXTENSIONS == ('.csv', '.xlsx')


def test_required_columns() -> None:
    '''Ensure pt-BR headers required from user.'''
    assert config.PT_REQUIRED_COLUMNS == ('Data', 'Descrição', 'Valor')


def test_app_version() -> None:
    '''Ensure version snapshot exists for reports.'''
    assert config.APP_VERSION == '1.0.0'
