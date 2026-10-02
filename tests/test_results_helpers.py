'''Headless checks for section 3 display helpers.'''

import pandas as pd

from src.display import to_amount_text
from src.labels import reason_short
from src.money import clean_brl_text, format_brl
from ui.components.base import side_triple
from ui.components.match_display import build_duplicate_display, build_match_display
from ui.components.review_cards import review_option_label
from ui.sections.results import _next_action_line, _tab_label
from ui.sections.review import _remaining_label


def test_reason_short_maps_codes() -> None:
    '''Every engine code maps to pt-BR short badge.'''
    assert reason_short('regra_composta_ok') == 'Confere'
    assert reason_short('descricao_baixa_similaridade') == 'Baixa similaridade'
    assert reason_short('descricao_divergente') == 'Descrição divergente'
    assert reason_short('divergencia_centavos') == 'Centavos'
    assert reason_short('divergencia_valor_descricao') == 'Valor e descrição'
    assert reason_short('ambiguidade_multipla') == 'Múltiplos candidatos'
    assert reason_short('sem_candidato') == 'Sem candidato'
    assert reason_short('data_fora_tolerancia') == 'Data fora da tolerância'
    assert reason_short('valor_fora_tolerancia') == 'Valor fora da tolerância'
    assert reason_short('sinal_bloqueado') == 'Sinal oposto'
    assert reason_short('duplicada_suspeita') == 'Duplicada suspeita'


def test_reason_short_accepts_long_label() -> None:
    '''Long pt-BR motive maps to same short badge.'''
    assert reason_short('Valor, data e descrição conferem') == 'Confere'
    assert reason_short('Sinal oposto (débito x crédito)') == 'Sinal oposto'
    assert reason_short('Múltiplos candidatos possíveis') == 'Múltiplos candidatos'


def test_reason_short_missing_never_leaks_english() -> None:
    '''Missing motives fall back to dash without None nan.'''
    assert reason_short(None) == '—'
    assert reason_short(float('nan')) == '—'
    assert reason_short('') == '—'
    assert reason_short('—') == '—'
    assert reason_short('unknown_code') == 'unknown_code'


def test_next_action_line_branches() -> None:
    '''Action line covers empty singular plural mixes.'''
    assert _next_action_line(0, 0) == 'Tudo resolvido — nada aguarda ação.'
    assert _next_action_line(1, 0) == '1 par aguarda revisão.'
    assert _next_action_line(3, 0) == '3 pares aguardam revisão.'
    assert _next_action_line(0, 1) == '1 item sem par.'
    assert _next_action_line(0, 4) == '4 itens sem par.'
    assert _next_action_line(2, 3) == '2 pares aguardam revisão • 3 itens sem par.'
    assert _next_action_line(1, 1) == '1 par aguarda revisão • 1 item sem par.'


def test_tab_label_hides_zero() -> None:
    '''Zero counts hide while positive counts show.'''
    assert _tab_label(':material/check_circle:', 'Conciliadas', 0) == (
        ':material/check_circle: Conciliadas'
    )
    assert _tab_label(':material/check_circle:', 'Conciliadas', 5) == (
        ':material/check_circle: Conciliadas (5)'
    )


def test_remaining_label_singular_plural() -> None:
    '''Remaining caption uses pt-BR singular plural.'''
    assert _remaining_label(0) == 'Nenhum par para revisar.'
    assert _remaining_label(1) == 'Falta 1 par para revisar.'
    assert _remaining_label(2) == 'Faltam 2 pares para revisar.'


def test_side_triple_extracts_date_description_amount() -> None:
    '''Public triple reads base row by index.'''
    statement, _ = _make_side_frames()
    date_val, desc_val, amount_val = side_triple(statement, 0)
    assert date_val == '10/09/2026'
    assert desc_val == 'Pagamento X'
    assert amount_val == '-2500'


def _make_side_frames() -> tuple:
    '''Build minimal extrato interno side frames.'''
    statement = pd.DataFrame([{'Data': '10/09/2026', 'Descrição': 'Pagamento X', 'Valor': '-2500'}])
    ledger = pd.DataFrame([{'Data': '10/09/2026', 'Descrição': 'X NF 1', 'Valor': '-2500'}])
    return statement, ledger


def test_build_duplicate_display_empty() -> None:
    '''Empty duplicates keep single side columns.'''
    statement, ledger = _make_side_frames()
    frame = build_duplicate_display(pd.DataFrame(), statement, ledger)
    assert list(frame.columns) == _duplicate_columns()
    assert len(frame) == 0
    none_frame = build_duplicate_display(None, statement, ledger)
    assert list(none_frame.columns) == list(frame.columns)


def _duplicate_columns() -> list:
    '''Return expected single side duplicate headers.'''
    return ['Par ID', 'Base', 'Data', 'Descrição', 'Valor', 'Regra', 'Motivo']


def test_build_duplicate_display_sides() -> None:
    '''Each duplicate row reads only its own base.'''
    statement, ledger = _make_side_frames()
    dup = pd.DataFrame(
        [
            {
                'match_id': 'dup-statement-0',
                'source': 'statement',
                'statement_idx': 0,
                'ledger_idx': 0,
                'rule_id': 'RN-04',
                'reason': 'duplicada_suspeita',
            },
            {
                'match_id': 'dup-ledger-0',
                'source': 'ledger',
                'statement_idx': 0,
                'ledger_idx': 0,
                'rule_id': 'RN-04',
                'reason': 'duplicada_suspeita',
            },
        ]
    )
    frame = build_duplicate_display(dup, statement, ledger)
    assert frame.iloc[0]['Base'] == 'Extrato'
    assert frame.iloc[0]['Descrição'] == 'Pagamento X'
    assert frame.iloc[1]['Base'] == 'Interno'
    assert frame.iloc[1]['Descrição'] == 'X NF 1'
    assert frame.iloc[0]['Motivo'] == 'Duplicada suspeita'


def test_build_duplicate_display_unknown_source() -> None:
    '''Unknown source never poses as Interno.'''
    statement, ledger = _make_side_frames()
    dup = pd.DataFrame(
        [
            {
                'match_id': 'dup-x-0',
                'source': None,
                'statement_idx': 0,
                'ledger_idx': 0,
                'rule_id': 'RN-04',
                'reason': 'duplicada_suspeita',
            }
        ]
    )
    frame = build_duplicate_display(dup, statement, ledger)
    assert frame.iloc[0]['Base'] == '—'


def test_build_match_display_manual_column_conditional() -> None:
    '''Manual action column appears only with marks.'''
    statement, ledger = _make_side_frames()
    match = pd.DataFrame(
        [
            {
                'match_id': 's0-l0',
                'statement_idx': 0,
                'ledger_idx': 0,
                'day_diff': 0,
                'value_diff': 0,
                'description_score': 90,
                'rule_id': 'RN-07',
                'reason': 'ambiguidade_multipla',
            }
        ]
    )
    plain = build_match_display(match, statement, ledger, set())
    assert 'Ação manual' not in list(plain.columns)
    assert plain.iloc[0]['Motivo'] == 'Múltiplos candidatos possíveis'
    marked = build_match_display(match, statement, ledger, {'s0-l0'})
    assert 'Ação manual' in list(marked.columns)
    assert marked.iloc[0]['Ação manual'] == 'Confirmada manualmente'
    empty = build_match_display(pd.DataFrame(), statement, ledger, {'s0-l0'})
    assert 'Ação manual' not in list(empty.columns)


def test_review_option_label_friendly_without_codes() -> None:
    '''Select label shows triple plus motive without ids.'''
    statement, _ = _make_side_frames()
    row = pd.Series({'match_id': 's0-l0', 'statement_idx': 0, 'reason': 'sinal_bloqueado'})
    label = review_option_label(row, statement)
    assert 'Sinal oposto' in label
    assert 'sinal_bloqueado' not in label
    assert 's0-l0' not in label
    assert '10/09/2026' in label
    assert 'Pagamento X' in label


def test_review_option_label_missing_never_leaks() -> None:
    '''Missing reason or frame never leaks None nan.'''
    statement, _ = _make_side_frames()
    assert review_option_label(pd.Series({'reason': 'sinal_bloqueado'}), None) == 'Sinal oposto'
    assert review_option_label(pd.Series({'reason': None}), None) == '—'
    assert review_option_label(pd.Series({'reason': float('nan')}), None) == '—'
    missing = pd.Series({'reason': None, 'statement_idx': 0})
    label = review_option_label(missing, statement)
    assert 'None' not in label
    assert 'nan' not in label


def test_review_option_label_truncates_long_description() -> None:
    '''Long descriptions collapse to single line with ellipsis.'''
    statement = pd.DataFrame(
        [{'Data': '10/09/2026', 'Descrição': 'X' * 60, 'Valor': '-2500'}]
    )
    row = pd.Series({'match_id': 's0-l0', 'statement_idx': 0, 'reason': 'sinal_bloqueado'})
    label = review_option_label(row, statement)
    assert '…' in label
    assert 'X' * 60 not in label


def test_negative_brl_prefix_round_trip() -> None:
    '''Negative prefix survives clean and display round trip.'''
    assert format_brl('-2500') == '-R$ 2.500,00'
    assert clean_brl_text('-R$ 2.500,00') == '-2500.00'
    assert to_amount_text('-R$ 2.500,00') == '-R$ 2.500,00'
