'''Loader ingestion checks.'''

from pathlib import Path

import pandas as pd
import pytest

import src.loader as loader
import src.mapping as mapping
from src.loader import (
    detect_delimiter,
    detect_encoding,
    get_preview,
    load_table,
    validate_not_empty,
)


def test_load_csv_utf8(fixture_paths: dict) -> None:
    '''Load utf8 csv preserving header and metadata.'''
    frame, meta = load_table(fixture_paths['statement'])
    assert list(frame.columns) == ['Data', 'Descrição', 'Valor']
    assert len(frame) == 2
    assert meta['encoding'] == 'utf-8'
    assert meta['delimiter'] == ','


def test_load_excel(fixture_paths: dict) -> None:
    '''Load xlsx first sheet preserving header.'''
    frame, meta = load_table(fixture_paths['ledger'])
    assert list(frame.columns) == ['Data', 'Descrição', 'Valor']
    assert len(frame) == 2
    assert meta['sheet'] is not None


def test_load_latin1_semicolon(fixture_paths: dict) -> None:
    '''Load latin1 semicolon csv with detected settings.'''
    target = Path(fixture_paths['matrix']) / 'latin1_ponto_virgula.csv'
    frame, meta = load_table(target)
    assert len(frame) == 2
    assert meta['encoding'] == 'latin1'
    assert meta['delimiter'] == ';'
    assert list(frame.columns) == ['Data', 'Descrição', 'Valor']


def test_reject_pdf(fixture_paths: dict) -> None:
    '''Reject pdf with clear pt-BR message.'''
    target = Path(fixture_paths['matrix']) / 'invalido.pdf'
    with pytest.raises(ValueError, match='Formato não suportado'):
        load_table(target)


def test_reject_empty(fixture_paths: dict) -> None:
    '''Block header only file with pt-BR message.'''
    target = Path(fixture_paths['matrix']) / 'vazio.csv'
    frame, _ = load_table(target)
    with pytest.raises(ValueError, match='Arquivo vazio'):
        validate_not_empty(frame)


def test_reject_oversize(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    '''Block files above size limit without creating 20 MB file.'''
    target = tmp_path / 'sample.csv'
    target.write_text('Data,Descrição,Valor\n10/09/2026,X,100\n', encoding='utf-8')
    monkeypatch.setattr(loader, 'MAX_FILE_SIZE_MB', 0)
    with pytest.raises(ValueError, match='Arquivo acima de 20 MB'):
        load_table(target)


def test_reject_path_traversal() -> None:
    '''Reject traversal names with pt-BR message.'''
    with pytest.raises(ValueError, match='Nome de arquivo inválido'):
        load_table(Path('../../etc/passwd.csv'))


def test_preview_returns_five() -> None:
    '''Preview returns at most five rows.'''
    frame = pd.DataFrame({'Data': range(10), 'Descrição': range(10), 'Valor': range(10)})
    preview = get_preview(frame, n=5)
    assert len(preview) == 5


def test_detect_delimiter_comma(fixture_paths: dict) -> None:
    '''Detect comma for utf8 fixture.'''
    encoding = detect_encoding(fixture_paths['statement'])
    assert detect_delimiter(fixture_paths['statement'], encoding) == ','


def test_detect_delimiter_semicolon(fixture_paths: dict) -> None:
    '''Detect semicolon for latin1 fixture.'''
    target = Path(fixture_paths['matrix']) / 'latin1_ponto_virgula.csv'
    encoding = detect_encoding(target)
    assert encoding == 'latin1'
    assert detect_delimiter(target, encoding) == ';'


def test_detect_encoding_utf8(fixture_paths: dict) -> None:
    '''Detect utf8 for standard fixture.'''
    assert detect_encoding(fixture_paths['statement']) == 'utf-8'


def test_auto_map_lowercase(fixture_paths: dict) -> None:
    '''Auto map lowercase header without accent.'''
    target = Path(fixture_paths['matrix']) / 'header_minusculo.csv'
    frame, _ = load_table(target)
    found = mapping.auto_map_columns(frame)
    assert found['data'] == 'data'
    assert found['descricao'] == 'descricao'
    assert found['valor'] == 'valor'


def test_auto_map_standard(fixture_paths: dict) -> None:
    '''Auto map standard pt-BR header.'''
    frame, _ = load_table(fixture_paths['statement'])
    found = mapping.auto_map_columns(frame)
    assert found['data'] == 'Data'
    assert found['descricao'] == 'Descrição'
    assert found['valor'] == 'Valor'


def test_apply_mapping_preserves_originals(fixture_paths: dict) -> None:
    '''Apply mapping keeps originals and adds internal fields.'''
    frame, _ = load_table(fixture_paths['statement'])
    found = mapping.auto_map_columns(frame)
    result = mapping.apply_mapping(frame, found)
    assert 'Data' in list(result.columns)
    assert 'Descrição' in list(result.columns)
    assert 'Valor' in list(result.columns)
    assert 'event_date' in list(result.columns)
    assert 'description' in list(result.columns)
    assert 'amount' in list(result.columns)


def test_apply_mapping_missing_column(fixture_paths: dict) -> None:
    '''Missing required column blocks with pt-BR message.'''
    frame, _ = load_table(fixture_paths['statement'])
    broken = {'data': 'Data', 'descricao': 'Descrição', 'valor': None}
    with pytest.raises(ValueError, match='Coluna obrigatória não encontrada'):
        mapping.apply_mapping(frame, broken)


def test_get_mapping_options(fixture_paths: dict) -> None:
    '''Expose original columns for interface selection.'''
    frame, _ = load_table(fixture_paths['statement'])
    options = mapping.get_mapping_options(frame)
    assert options == ['Data', 'Descrição', 'Valor']


def test_normalize_header_none() -> None:
    '''None header normalizes to empty string.'''
    assert mapping.normalize_header(None) == ''
    assert mapping.normalize_header('Descrição') == 'descricao'
    assert mapping.normalize_header('Histórico') == 'historico'
    assert mapping.normalize_header('Amount') == 'amount'


def test_detect_delimiter_empty(tmp_path: Path) -> None:
    '''Empty file defaults to comma delimiter.'''
    target = tmp_path / 'empty.csv'
    target.write_text('', encoding='utf-8')
    assert detect_delimiter(target, 'utf-8') == ','
