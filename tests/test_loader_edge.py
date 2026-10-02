'''Loader security xls corrupt absolute checks.'''

import tempfile
from pathlib import Path

import pytest

from src.loader import load_table


def test_reject_xls_legacy(tmp_path: Path) -> None:
    '''Legacy xls rejected with pt-BR message.'''
    target = tmp_path / 'legacy.xls'
    target.write_bytes(b'not excel')
    with pytest.raises(ValueError, match='Formato não suportado'):
        load_table(target)


def test_reject_truncated_xlsx(tmp_path: Path) -> None:
    '''Truncated zip raises pt-BR readable error.'''
    target = tmp_path / 'broken.xlsx'
    target.write_bytes(b'PK\x03\x04 truncated bytes')
    with pytest.raises(ValueError, match='Não foi possível ler o arquivo'):
        load_table(target)


def test_reject_absolute_outside() -> None:
    '''Absolute outside work temp blocked pt-BR.'''
    with pytest.raises(ValueError, match='Nome de arquivo inválido'):
        load_table(Path('/etc/passwd.csv'))


def test_allow_absolute_inside_work(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    '''Absolute inside work dir loads when valid.'''
    import pathlib

    work_file = Path.cwd() / 'tests' / 'fixtures' / 'extrato.csv'
    frame, _ = load_table(work_file.resolve())
    assert len(frame) == 2
    assert pathlib.Path(str(work_file)).is_absolute()


def test_allow_temp_file(tmp_path: Path) -> None:
    '''Temp file inside system temp loads.'''
    payload = 'Data,Descrição,Valor\n10/09/2026,X,100\n'
    tmp = Path(tempfile.gettempdir()) / 'loader_temp_check.csv'
    tmp.write_text(payload, encoding='utf-8')
    try:
        frame, _ = load_table(tmp)
        assert len(frame) == 1
    finally:
        tmp.unlink(missing_ok=True)


def test_fetch_raw_table_truncated_returns_none(monkeypatch: pytest.MonkeyPatch) -> None:
    '''Corrupted upload returns none with pt-BR feedback.'''
    import streamlit as st

    from ui.sections.upload.file_io import fetch_raw_table

    class FakeUpload:
        name = 'broken.xlsx'

        def getbuffer(self) -> bytes:
            return b'PK\x03\x04 truncated bytes'

    messages: list = []
    monkeypatch.setattr(st, 'error', lambda msg: messages.append(msg))
    result = fetch_raw_table(FakeUpload())
    assert result is None
    assert len(messages) == 1
    assert 'Não foi possível ler' in messages[0] or 'Formato' in messages[0]
