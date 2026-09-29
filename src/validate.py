'''Row level validation splitting valid and error tables.'''

import pandas as pd

from src.logger import get_logger

logger = get_logger(__name__)


def collect_errors(frame: pd.DataFrame) -> tuple:
    '''Split normalized table into valid rows and pt-BR error table.'''
    valid_keys: list = []
    records: list = []
    if 'error_code' not in list(frame.columns):
        return frame.copy(), pd.DataFrame(columns=['Linha', 'Motivo', 'Orientação'])
    for pos, item in enumerate(frame.iterrows()):
        idx, row = item
        try:
            line_no = _resolve_line_number(idx, pos)
            code = row.get('error_code')
            if isinstance(code, str) and code.strip() != '':
                motive, guidance = _build_error_message(code, line_no)
                records.append(
                    {'Linha': line_no, 'Motivo': motive, 'Orientação': guidance}
                )
            else:
                valid_keys.append(idx)
        except Exception as exc:
            logger.warning(f'Error collection failed with {exc}')
            continue
    valid = frame.loc[valid_keys].copy() if valid_keys else frame.iloc[0:0].copy()
    errors = pd.DataFrame(records, columns=['Linha', 'Motivo', 'Orientação'])
    logger.info(f'Collected {len(errors)} errors from {len(frame)} rows')
    return valid, errors


def _resolve_line_number(idx: object, pos: int) -> int:
    '''Resolve spreadsheet line number from index and position.'''
    try:
        return int(idx) + 2
    except (ValueError, TypeError):
        return pos + 2


def _build_error_message(code: str, line_no: int) -> tuple:
    '''Build actionable pt-BR motive and guidance for error code.'''
    if code == 'DATA_INVALIDA':
        motive = f'Data inválida na linha {line_no}. Use DD/MM/AAAA.'
        guidance = 'Corrija a data para DD/MM/AAAA e reimporte o arquivo.'
        return motive, guidance
    if code == 'VALOR_INVALIDO':
        motive = f'Valor inválido na linha {line_no}. Ex.: -R$ 2.500,00.'
        guidance = 'Corrija o valor usando número com sinal e reimporte o arquivo.'
        return motive, guidance
    if code == 'COLUNA_AUSENTE':
        motive = (
            f'Coluna obrigatória não encontrada na linha {line_no}. '
            'Verifique o modelo com colunas Data, Descrição, Valor.'
        )
        guidance = 'Mapeie manualmente as colunas Data, Descrição e Valor.'
        return motive, guidance
    motive = f'Erro na linha {line_no}. Verifique os dados.'
    guidance = 'Corrija a linha e reimporte o arquivo.'
    return motive, guidance
