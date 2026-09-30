'''Synthetic benchmark for matching engine.'''

import time

import pandas as pd

from src.classifier import build_result_tables
from src.config import MAX_ROWS_WARNING
from src.guards import warn_volume as _shared_warn_volume
from src.logger import get_logger
from src.mapping import apply_mapping, auto_map_columns
from src.matcher import build_params
from src.normalize import normalize_table

logger = get_logger(__name__)


def build_synthetic_frame(count: int, source: str) -> pd.DataFrame:
    '''Build normalized frame with distinct amounts.'''
    rows: list = []
    for pos in range(count):
        day = 10 + (pos % 20)
        rows.append((f'{day:02d}/09/2026', f'alpha {pos}', str(1000 + pos)))
    frame = pd.DataFrame(rows, columns=['Data', 'Descrição', 'Valor'])
    mapped = apply_mapping(frame, auto_map_columns(frame))
    return normalize_table(mapped, source)


def run_bench(count: int = 5000) -> float:
    '''Run count versus count matching returning seconds.'''
    _warn_volume(count, count)
    statement = build_synthetic_frame(count, 'statement')
    ledger = build_synthetic_frame(count, 'ledger')
    params = build_params()
    started = time.perf_counter()
    tables = build_result_tables(statement, ledger, params)
    elapsed = time.perf_counter() - started
    total = len(tables.get('auto')) + len(tables.get('potential'))
    logger.info(f'Bench {count}x{count} finished in {elapsed:.2f}s with {total} pairs.')
    return elapsed


def _warn_volume(statement_count: int, ledger_count: int) -> None:
    '''Warn pt-BR when synthetic volume may degrade.'''
    _shared_warn_volume(statement_count, ledger_count, MAX_ROWS_WARNING)


def main() -> None:
    '''Execute five thousand benchmark asserting thirty seconds.'''
    elapsed = run_bench(5000)
    if elapsed >= 30.0:
        raise SystemExit(f'Benchmark excedeu 30s com {elapsed:.2f}s.')
    logger.info('Benchmark dentro do limite de 30s.')


if __name__ == '__main__':
    main()
