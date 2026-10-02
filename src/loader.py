'''Ingestion of bank and ledger tables.'''

import csv
import tempfile
from decimal import InvalidOperation
from pathlib import Path
from zipfile import BadZipFile

import pandas as pd
from openpyxl.utils.exceptions import InvalidFileException

from src.config import MAX_FILE_SIZE_MB, SUPPORTED_EXTENSIONS
from src.logger import get_logger

logger = get_logger(__name__)


def detect_encoding(path: Path | str) -> str:
    '''Detect file encoding trying utf-8 before latin1.'''
    target = Path(path)
    try:
        with target.open('r', encoding='utf-8') as handle:
            handle.read(8192)
        return 'utf-8'
    except UnicodeError:
        return 'latin1'


def detect_delimiter(path: Path | str, encoding: str) -> str:
    '''Detect csv delimiter choosing consistent column count.'''
    target = Path(path)
    with target.open('r', encoding=encoding, newline='') as handle:
        sample = [handle.readline() for _ in range(5)]
    rows = [line for line in sample if line.strip() != '']
    if not rows:
        return ','
    best = ','
    best_score = -1
    for candidate in (',', ';'):
        counts = []
        for line in rows:
            parsed = list(csv.reader([line], delimiter=candidate))
            if parsed:
                counts.append(len(parsed[0]))
        score = counts[0] if counts and len(set(counts)) == 1 else 0
        if score > best_score:
            best_score = score
            best = candidate
    return best


def load_table(path: Path | str) -> tuple[pd.DataFrame, dict]:
    '''Load raw table with metadata preserving original header.'''
    logger.info(f'Loading table from {path}')
    target = Path(path)
    _ensure_safe_path(target)
    _ensure_supported_extension(target)
    _ensure_size_limit(target)
    suffix = target.suffix.lower()
    if suffix == '.csv':
        return _load_csv(target)
    return _load_excel(target)


def get_preview(frame: pd.DataFrame, n: int = 5) -> pd.DataFrame:
    '''Return first rows for interface preview.'''
    return frame.head(n)


def validate_not_empty(frame: pd.DataFrame) -> None:
    '''Block empty files with actionable pt-BR error.'''
    if frame.empty:
        raise ValueError(
            'Arquivo vazio. Verifique o modelo com colunas Data, Descrição, Valor.'
        )


def _ensure_safe_path(target: Path) -> None:
    '''Reject traversal null bytes and absolute outside work temp.'''
    if '..' in target.parts:
        raise ValueError('Nome de arquivo inválido. Verifique o arquivo enviado.')
    if '\x00' in str(target):
        raise ValueError('Nome de arquivo inválido. Verifique o arquivo enviado.')
    if target.is_absolute():
        _ensure_absolute_allowed(target)


def _ensure_supported_extension(target: Path) -> None:
    '''Reject unsupported extensions with pt-BR message.'''
    if target.suffix.lower() not in SUPPORTED_EXTENSIONS:
        raise ValueError('Formato não suportado. Envie CSV ou Excel.')


def _ensure_absolute_allowed(target: Path) -> None:
    '''Allow absolute only inside work dir or system temp.'''
    try:
        resolved = target.resolve()
    except OSError as exc:
        logger.warning(f'Path resolve failed with {exc}')
        raise ValueError('Nome de arquivo inválido. Verifique o arquivo enviado.') from exc
    work = Path.cwd().resolve()
    temp = Path(tempfile.gettempdir()).resolve()
    if resolved.is_relative_to(work):
        return
    if resolved.is_relative_to(temp):
        return
    raise ValueError('Nome de arquivo inválido. Verifique o arquivo enviado.')


def _ensure_size_limit(target: Path) -> None:
    '''Reject files above configured size limit.'''
    limit = MAX_FILE_SIZE_MB * 1024 * 1024
    if target.stat().st_size > limit:
        raise ValueError('Arquivo acima de 20 MB.')


def _load_csv(target: Path) -> tuple[pd.DataFrame, dict]:
    '''Read csv with detected encoding and delimiter.'''
    encoding = detect_encoding(target)
    delimiter = detect_delimiter(target, encoding)
    frame = pd.read_csv(target, encoding=encoding, delimiter=delimiter)
    meta = {'encoding': encoding, 'delimiter': delimiter, 'sheet': None}
    logger.info(f'Loaded csv with {len(frame)} rows')
    return frame, meta


def _load_excel(target: Path) -> tuple[pd.DataFrame, dict]:
    '''Read first xlsx sheet rejecting legacy xls zip errors.'''
    if target.suffix.lower() != '.xlsx':
        raise ValueError('Formato não suportado. Envie CSV ou Excel.')
    try:
        book = pd.ExcelFile(target, engine='openpyxl')
        name = book.sheet_names[0] if book.sheet_names else None
        frame = pd.read_excel(target, sheet_name=0, engine='openpyxl')
    except ValueError as exc:
        logger.warning(f'Excel load failed with {exc}')
        raise ValueError('Não foi possível ler o arquivo. Verifique o formato.') from exc
    except (BadZipFile, InvalidFileException, KeyError, OSError, RuntimeError) as exc:
        logger.warning(f'Excel load failed with {exc}')
        raise ValueError('Não foi possível ler o arquivo. Verifique o formato.') from exc
    except InvalidOperation as exc:
        logger.warning(f'Excel load failed with {exc}')
        raise ValueError('Não foi possível ler o arquivo. Verifique o formato.') from exc
    meta = {'encoding': None, 'delimiter': None, 'sheet': name}
    logger.info(f'Loaded excel sheet {name} with {len(frame)} rows')
    return frame, meta
