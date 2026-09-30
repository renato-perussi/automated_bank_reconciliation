'''Streamlit interface for bank reconciliation flow.'''

import tempfile
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

import pandas as pd
import streamlit as st

from src.classifier import build_result_tables
from src.config import APP_VERSION, DATE_TOLERANCE_DAYS, FUZZY_THRESHOLD, VALUE_TOLERANCE
from src.loader import get_preview, load_table, validate_not_empty
from src.logger import get_logger
from src.mapping import apply_mapping, auto_map_columns, get_mapping_options
from src.matcher import build_params
from src.normalize import normalize_table
from src.validate import collect_errors
from ui.components import (
    build_comparison_frame,
    build_match_display,
    build_pending_side,
    calc_kpis,
    format_brl,
    format_pct,
    load_styles,
    render_header,
    render_kpi_card,
    render_status_table,
)

logger = get_logger(__name__)


def init_state() -> None:
    '''Ensure session keys for flow state.'''
    if 'statement_df' not in st.session_state:
        st.session_state['statement_df'] = None
    if 'ledger_df' not in st.session_state:
        st.session_state['ledger_df'] = None
    if 'params' not in st.session_state:
        st.session_state['params'] = build_params()
    if 'results' not in st.session_state:
        st.session_state['results'] = None
    if 'review_log' not in st.session_state:
        st.session_state['review_log'] = []
    if 'manual_confirmed' not in st.session_state:
        st.session_state['manual_confirmed'] = set()
    if 'manual_rejected' not in st.session_state:
        st.session_state['manual_rejected'] = set()
    if 'statement_errors' not in st.session_state:
        st.session_state['statement_errors'] = pd.DataFrame()
    if 'ledger_errors' not in st.session_state:
        st.session_state['ledger_errors'] = pd.DataFrame()
    if 'feedback' not in st.session_state:
        st.session_state['feedback'] = None


def save_temp_file(uploaded_file: object) -> Path | None:
    '''Persist upload preserving suffix for loader.'''
    try:
        raw_name = str(getattr(uploaded_file, 'name', 'upload.csv'))
        suffix = Path(raw_name).suffix.lower()
        if suffix == '':
            suffix = '.csv'
        payload = uploaded_file.getbuffer()
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
        tmp.write(bytes(payload))
        tmp.close()
        return Path(tmp.name)
    except (OSError, ValueError, AttributeError) as exc:
        logger.warning(f'Temp save failed with {exc}')
        st.error('Não foi possível salvar o arquivo. Tente novamente.')
        return None


def fetch_raw_table(uploaded_file: object) -> pd.DataFrame | None:
    '''Load raw table from upload with pt-BR feedback.'''
    temp_path = save_temp_file(uploaded_file)
    if temp_path is None:
        return None
    try:
        frame, _ = load_table(temp_path)
        validate_not_empty(frame)
        return frame
    except ValueError as exc:
        st.error(str(exc))
        return None
    except (OSError, RuntimeError) as exc:
        logger.warning(f'Load failed with {exc}')
        st.error('Não foi possível ler o arquivo. Verifique o formato.')
        return None
    finally:
        try:
            temp_path.unlink(missing_ok=True)
        except OSError as exc:
            logger.warning(f'Cleanup failed with {exc}')


def choose_mapping(raw_frame: pd.DataFrame, prefix: str) -> dict:
    '''Collect column choices with auto mapped defaults.'''
    options = get_mapping_options(raw_frame)
    auto_map = auto_map_columns(raw_frame)
    date_default = _default_index(options, auto_map.get('data'))
    desc_default = _default_index(options, auto_map.get('descricao'))
    value_default = _default_index(options, auto_map.get('valor'))
    date_choice = st.selectbox('Data', options, index=date_default, key=f'{prefix}_date')
    desc_choice = st.selectbox('Descrição', options, index=desc_default, key=f'{prefix}_desc')
    value_choice = st.selectbox('Valor', options, index=value_default, key=f'{prefix}_value')
    return {'data': date_choice, 'descricao': desc_choice, 'valor': value_choice}


def _default_index(options: list, wished: object) -> int:
    '''Resolve default option position safely.'''
    try:
        return options.index(str(wished))
    except (ValueError, TypeError):
        return 0


def finalize_source(raw_frame: pd.DataFrame, mapping: dict, source: str) -> tuple:
    '''Normalize mapped table splitting valid and errors.'''
    try:
        mapped = apply_mapping(raw_frame, mapping)
        normalized = normalize_table(mapped, source)
        valid, errors = collect_errors(normalized)
        return valid, errors
    except ValueError as exc:
        st.error(str(exc))
        empty = raw_frame.iloc[0:0].copy()
        return empty, pd.DataFrame(columns=['Linha', 'Motivo', 'Orientação'])
    except (RuntimeError, KeyError) as exc:
        logger.warning(f'Normalize failed with {exc}')
        st.error('Não foi possível processar as colunas. Confira o mapeamento.')
        empty = raw_frame.iloc[0:0].copy()
        return empty, pd.DataFrame(columns=['Linha', 'Motivo', 'Orientação'])


def show_preview_errors(raw_frame: pd.DataFrame, error_frame: pd.DataFrame) -> None:
    '''Show five row preview plus pt-BR error table.'''
    st.markdown('<p class="body-text">Prévia (5 linhas)</p>', unsafe_allow_html=True)
    st.dataframe(get_preview(raw_frame, 5), use_container_width=True)
    if error_frame is not None and len(error_frame) > 0:
        st.markdown('<p class="body-text">Erros encontrados</p>', unsafe_allow_html=True)
        st.dataframe(error_frame, use_container_width=True)


def render_single_upload(
    uploader_label: str, source: str, frame_key: str, error_key: str, prefix: str
) -> None:
    '''Render one uploader with mapping preview errors.'''
    uploaded = st.file_uploader(uploader_label, type=['csv', 'xls', 'xlsx'], key=f'{prefix}_up')
    st.markdown(
        '<p class="upload-note">Limite 20 MB por arquivo • CSV ou Excel</p>',
        unsafe_allow_html=True,
    )
    if uploaded is None:
        return
    raw_frame = fetch_raw_table(uploaded)
    if raw_frame is None:
        return
    mapping = choose_mapping(raw_frame, prefix)
    valid, errors = finalize_source(raw_frame, mapping, source)
    st.session_state[frame_key] = valid
    st.session_state[error_key] = errors
    show_preview_errors(raw_frame, errors)


def render_upload_section() -> None:
    '''Render two side by side upload cards.'''
    st.markdown('<h2 class="display-md">1 Upload dos arquivos</h2>', unsafe_allow_html=True)
    st.markdown(
        '<p class="body-text">Envie o extrato e os lançamentos internos em CSV ou Excel.</p>',
        unsafe_allow_html=True,
    )
    left, right = st.columns(2)
    with left:
        with st.container(border=True):
            render_single_upload(
                'Extrato bancário (CSV ou Excel)',
                'statement',
                'statement_df',
                'statement_errors',
                'statement',
            )
    with right:
        with st.container(border=True):
            render_single_upload(
                'Lançamentos internos (CSV ou Excel)',
                'ledger',
                'ledger_df',
                'ledger_errors',
                'ledger',
            )


def render_params_section() -> None:
    '''Render tolerance controls storing engine params.'''
    st.markdown('<h2 class="display-md">2 Parâmetros</h2>', unsafe_allow_html=True)
    date_tolerance_days = st.slider('Tolerância de dias', 0, 30, DATE_TOLERANCE_DAYS)
    st.markdown(
        '<p class="help-muted">2 dias cobre compensação D+1.</p>', unsafe_allow_html=True
    )
    fuzzy_threshold = st.slider('Similaridade mínima (%)', 0, 100, FUZZY_THRESHOLD)
    use_fuzzy = st.toggle('Usar similaridade de descrição', True)
    st.markdown(
        '<p class="help-muted">85 equilibra precisão e revisão manual.</p>', unsafe_allow_html=True
    )
    raw_tolerance = st.number_input(
        'Tolerância de valor (R$)', 0.00, 10.00, float(VALUE_TOLERANCE), step=0.01
    )
    st.markdown(
        '<p class="help-muted">0,00 exige valor exato. Ex.: 0,05 permite centavos.</p>',
        unsafe_allow_html=True,
    )
    try:
        st.session_state['params'] = build_params(
            date_tolerance_days=date_tolerance_days,
            fuzzy_threshold=fuzzy_threshold,
            value_tolerance=Decimal(str(raw_tolerance)),
            use_fuzzy=bool(use_fuzzy),
        )
    except ValueError as exc:
        st.error(str(exc))


def render_concile_button() -> None:
    '''Execute matching storing five result tables.'''
    pressed = st.button('Conciliar', key='concile_action', type='primary')
    if not pressed:
        return
    statement_frame = st.session_state.get('statement_df')
    ledger_frame = st.session_state.get('ledger_df')
    if statement_frame is None or ledger_frame is None:
        st.error('Envie os dois arquivos para conciliar.')
        return
    if len(statement_frame) == 0 or len(ledger_frame) == 0:
        st.error('Arquivos sem linhas válidas. Corrija os erros e tente novamente.')
        return
    try:
        params = st.session_state.get('params', build_params())
        st.session_state['results'] = build_result_tables(statement_frame, ledger_frame, params)
        st.session_state['manual_confirmed'] = set()
        st.session_state['manual_rejected'] = set()
        st.success('Conciliação concluída. Veja os resultados abaixo.')
    except ValueError as exc:
        st.error(str(exc))
    except (RuntimeError, KeyError) as exc:
        logger.warning(f'Matching failed with {exc}')
        st.error('Não foi possível conciliar. Verifique os arquivos e parâmetros.')


def _adjusted_counts() -> tuple:
    '''Compute effective auto potential after manual review.'''
    results = st.session_state.get('results')
    if results is None:
        return (0, 0, 0, 0, 0, 0, 0)
    confirmed = st.session_state.get('manual_confirmed', set())
    rejected = st.session_state.get('manual_rejected', set())
    auto_len = len(results.get('auto')) + len(confirmed)
    pot_len = len(results.get('potential')) - len(confirmed) - len(rejected)
    pot_len = pot_len if pot_len >= 0 else 0
    pending_len = len(results.get('pending')) + len(rejected)
    divergent_len = len(results.get('divergent'))
    duplicate_len = len(results.get('duplicate'))
    unified = auto_len + pot_len + pending_len + divergent_len + duplicate_len
    return (auto_len, pot_len, pending_len, divergent_len, duplicate_len, unified, len(confirmed))


def render_kpi_section() -> None:
    '''Render five indicators plus exception bar.'''
    results = st.session_state.get('results')
    if results is None:
        return
    statement_frame = st.session_state.get('statement_df')
    ledger_frame = st.session_state.get('ledger_df')
    statement_count = 0 if statement_frame is None else len(statement_frame)
    ledger_count = 0 if ledger_frame is None else len(ledger_frame)
    kpis = calc_kpis(results, statement_count, ledger_count)
    kpis = _apply_manual_kpis(kpis)
    st.markdown('<h2 class="display-md">3 Resultados</h2>', unsafe_allow_html=True)
    cols = st.columns(5)
    with cols[0]:
        render_kpi_card('Total extrato', str(kpis['total_statement']))
    with cols[1]:
        render_kpi_card('Total interno', str(kpis['total_ledger']))
    with cols[2]:
        render_kpi_card('% Conciliado', format_pct(kpis['pct_auto']))
    with cols[3]:
        render_kpi_card('% Para revisão', format_pct(kpis['pct_review']))
    with cols[4]:
        render_kpi_card('% Pendente/Divergente', format_pct(kpis['pct_pending']))
    st.progress(_safe_ratio(kpis['pct_auto']))
    st.markdown(
        f'<p class="body-text">Taxa de exceção: {format_pct(kpis["exception_rate"])}</p>',
        unsafe_allow_html=True,
    )


def _apply_manual_kpis(kpis: dict) -> dict:
    '''Adjust percentages for confirmed rejected pairs.'''
    auto_len, pot_len, pending_len, divergent_len, dup_len, unified, _ = _adjusted_counts()
    if unified == 0:
        return kpis
    pct_auto = round(auto_len / unified * 100, 1)
    pct_review = round(pot_len / unified * 100, 1)
    pending_div = pending_len + divergent_len + dup_len
    pct_pending = round(pending_div / unified * 100, 1) if unified else 0.0
    updated = dict(kpis)
    updated['pct_auto'] = float(pct_auto)
    updated['pct_review'] = float(pct_review)
    updated['pct_pending'] = float(pct_pending)
    updated['exception_rate'] = round(100.0 - pct_auto, 1)
    return updated


def _safe_ratio(pct: float) -> float:
    '''Convert percentage to progress ratio.'''
    try:
        ratio = float(pct) / 100.0
    except (ValueError, TypeError):
        return 0.0
    if ratio < 0.0:
        return 0.0
    if ratio > 1.0:
        return 1.0
    return ratio


def filter_by_text(frame: pd.DataFrame, query: str) -> pd.DataFrame:
    '''Filter display rows by description substring.'''
    if frame is None or len(frame) == 0:
        return frame
    clean = str(query).strip().lower()
    if clean == '':
        return frame
    mask = pd.Series([False] * len(frame), index=frame.index)
    for field in ['Descrição', 'Descrição extrato', 'Descrição interno']:
        if field in frame.columns:
            part = frame[field].astype(str).str.lower().str.contains(clean, na=False)
            mask = mask | part
    return frame[mask]


def filter_by_value(frame: pd.DataFrame, low: float, high: float) -> pd.DataFrame:
    '''Filter display rows by numeric value window.'''
    if frame is None or len(frame) == 0:
        return frame
    fields = ['Valor', 'Valor extrato', 'Valor interno']
    present = [item for item in fields if item in frame.columns]
    if not present:
        return frame
    keep = pd.Series([False] * len(frame), index=frame.index)
    for field in present:
        numeric = pd.to_numeric(frame[field], errors='coerce')
        part = (numeric >= low) & (numeric <= high)
        part = part.fillna(True)
        keep = keep | part
    return frame[keep]


def render_match_tab(
    match_frame: pd.DataFrame, prefix: str, empty_label: str
) -> None:
    '''Render matched table with search value filters.'''
    statement_frame = st.session_state.get('statement_df')
    ledger_frame = st.session_state.get('ledger_df')
    confirmed = st.session_state.get('manual_confirmed', set())
    rejected = st.session_state.get('manual_rejected', set())
    active = _active_frame(match_frame, prefix, confirmed, rejected)
    display = build_match_display(active, statement_frame, ledger_frame, confirmed)
    query = st.text_input('Buscar descrição', key=f'{prefix}_search')
    display = filter_by_text(display, query)
    low, high = _value_bounds(display)
    picked = st.slider('Valor', low, high, (low, high), key=f'{prefix}_value')
    display = filter_by_value(display, float(picked[0]), float(picked[1]))
    period = st.date_input('Período', value=None, key=f'{prefix}_period', format='DD/MM/YYYY')
    start, end = _normalize_period(period)
    display = filter_by_period(display, start, end)
    if len(display) == 0:
        st.markdown(f'<p class="body-text">{empty_label}</p>', unsafe_allow_html=True)
        return
    render_status_table(display)


def _active_frame(
    match_frame: pd.DataFrame, prefix: str, confirmed: set, rejected: set
) -> pd.DataFrame:
    '''Select visible rows honoring manual review sets.'''
    if match_frame is None:
        return pd.DataFrame()
    if prefix == 'auto':
        extra = _confirmed_rows(confirmed)
        if len(extra) == 0:
            return match_frame
        return pd.concat([match_frame, extra], ignore_index=True)
    if prefix == 'potential':
        if 'match_id' not in match_frame.columns:
            return match_frame
        blocked = set(confirmed) | set(rejected)
        return match_frame[~match_frame['match_id'].isin(blocked)]
    return match_frame


def _confirmed_rows(confirmed: set) -> pd.DataFrame:
    '''Collect confirmed rows from original potential table.'''
    results = st.session_state.get('results')
    if results is None or not confirmed:
        return pd.DataFrame()
    potential = results.get('potential')
    if potential is None or len(potential) == 0:
        return pd.DataFrame()
    return potential[potential['match_id'].isin(confirmed)]


def _value_bounds(display: pd.DataFrame) -> tuple:
    '''Infer slider bounds from display values.'''
    if display is None:
        return (0.0, 10000.0)
    try:
        if len(display) == 0:
            return (0.0, 10000.0)
        values = []
        for field in ['Valor', 'Valor extrato', 'Valor interno']:
            if field in display.columns:
                numeric = pd.to_numeric(display[field], errors='coerce').dropna()
                values.extend(numeric.tolist())
        if not values:
            return (0.0, 10000.0)
        low = float(min(values))
        high = float(max(values))
        if low == high:
            high = low + 1.0
        return (low, high)
    except (ValueError, TypeError):
        return (0.0, 10000.0)


def _parse_filter_date(raw: object) -> object:
    '''Convert cell value to date tolerating errors.'''
    if raw is None:
        return None
    try:
        if pd.isna(raw):
            return None
    except (ValueError, TypeError):
        pass
    if isinstance(raw, pd.Timestamp):
        return raw.date()
    if isinstance(raw, datetime):
        return raw.date()
    if isinstance(raw, date):
        return raw
    text = str(raw).strip()
    if text == '' or text == '—':
        return None
    parsed = pd.to_datetime(text, dayfirst=True, errors='coerce')
    try:
        if pd.isna(parsed):
            return None
    except (ValueError, TypeError):
        return None
    return parsed.date()


def _normalize_period(period: object) -> tuple:
    '''Normalize date input to start end dates.'''
    if period is None:
        return (None, None)
    if isinstance(period, (list, tuple)):
        if len(period) == 0:
            return (None, None)
        if len(period) == 1:
            single = _parse_filter_date(period[0])
            return (single, single)
        start = _parse_filter_date(period[0])
        end = _parse_filter_date(period[1])
        if start is not None and end is not None and end < start:
            return (end, start)
        return (start, end)
    single = _parse_filter_date(period)
    return (single, single)


def filter_by_period(frame: pd.DataFrame, start: object, end: object) -> pd.DataFrame:
    '''Filter display rows by date window.'''
    if frame is None or len(frame) == 0:
        return frame
    if start is None and end is None:
        return frame
    if start is None:
        start = end
    if end is None:
        end = start
    fields = ['Data', 'Data extrato', 'Data interno']
    present = [item for item in fields if item in frame.columns]
    if not present:
        return frame
    keep = pd.Series([False] * len(frame), index=frame.index)
    for field in present:
        dates = frame[field].map(_parse_filter_date)
        part = dates.map(lambda item: item is not None and start <= item <= end)
        keep = keep | part.fillna(False)
    return frame[keep]


def _pending_bounds(left: pd.DataFrame, right: pd.DataFrame) -> tuple:
    '''Combine pending sides for slider bounds.'''
    if left is None or len(left) == 0:
        return _value_bounds(right)
    if right is None or len(right) == 0:
        return _value_bounds(left)
    try:
        combined = pd.concat([left, right], ignore_index=True)
    except (ValueError, TypeError):
        return _value_bounds(left)
    return _value_bounds(combined)


def render_pending_tab() -> None:
    '''Render two unmatched tables with filters.'''
    results = st.session_state.get('results')
    pending = results.get('pending') if results else pd.DataFrame()
    statement_frame = st.session_state.get('statement_df')
    ledger_frame = st.session_state.get('ledger_df')
    query = st.text_input('Buscar descrição', key='pending_search')
    left_base = build_pending_side(pending, statement_frame, 'statement')
    left_base = filter_by_text(left_base, query)
    right_base = build_pending_side(pending, ledger_frame, 'ledger')
    right_base = filter_by_text(right_base, query)
    low, high = _pending_bounds(left_base, right_base)
    picked = st.slider('Valor', low, high, (low, high), key='pending_value')
    left_display = filter_by_value(left_base, float(picked[0]), float(picked[1]))
    right_display = filter_by_value(right_base, float(picked[0]), float(picked[1]))
    period = st.date_input('Período', value=None, key='pending_period', format='DD/MM/YYYY')
    start, end = _normalize_period(period)
    left_display = filter_by_period(left_display, start, end)
    right_display = filter_by_period(right_display, start, end)
    st.markdown('<p class="body-text">Extrato sem par</p>', unsafe_allow_html=True)
    render_status_table(left_display)
    st.markdown('<p class="body-text">Interno sem par</p>', unsafe_allow_html=True)
    render_status_table(right_display)


def render_error_tab() -> None:
    '''Render combined file error tables.'''
    statement_errors = st.session_state.get('statement_errors')
    ledger_errors = st.session_state.get('ledger_errors')
    st.markdown('<p class="body-text">Erros do extrato</p>', unsafe_allow_html=True)
    render_status_table(statement_errors)
    st.markdown('<p class="body-text">Erros do interno</p>', unsafe_allow_html=True)
    render_status_table(ledger_errors)


def render_results_section() -> None:
    '''Render six tabs with pt-BR tables.'''
    results = st.session_state.get('results')
    if results is None:
        return
    tabs = st.tabs(
        ['Conciliadas', 'Para revisão', 'Pendentes', 'Divergentes', 'Duplicadas', 'Erros']
    )
    with tabs[0]:
        render_match_tab(results.get('auto'), 'auto', 'Nenhuma conciliada ainda.')
    with tabs[1]:
        render_match_tab(results.get('potential'), 'potential', 'Nenhum par para revisão.')
    with tabs[2]:
        render_pending_tab()
    with tabs[3]:
        render_match_tab(results.get('divergent'), 'divergent', 'Nenhuma divergência.')
    with tabs[4]:
        render_match_tab(results.get('duplicate'), 'duplicate', 'Nenhuma duplicada.')
    with tabs[5]:
        render_error_tab()


def render_review_section() -> None:
    '''Render side by side review with confirm reject.'''
    results = st.session_state.get('results')
    if results is None:
        return
    potential = results.get('potential')
    if potential is None or len(potential) == 0:
        return
    st.markdown('<h2 class="display-md">Revisão lado a lado</h2>', unsafe_allow_html=True)
    confirmed = st.session_state.get('manual_confirmed', set())
    rejected = st.session_state.get('manual_rejected', set())
    available = potential[~potential['match_id'].isin(set(confirmed) | set(rejected))]
    if len(available) == 0:
        st.markdown(
            '<p class="body-text">Nenhum par disponível para revisão.</p>', unsafe_allow_html=True
        )
        render_history()
        return
    options = available['match_id'].astype(str).tolist()
    chosen = st.selectbox('Selecione o par para revisão', options, key='review_pick')
    row = available[available['match_id'].astype(str) == str(chosen)].iloc[0]
    render_pair_detail(row)
    confirm_col, reject_col, _ = st.columns([1, 1, 3])
    with confirm_col:
        if st.button('Confirmar', key='confirm_pair', type='primary', use_container_width=True):
            confirm_pair(str(chosen))
    with reject_col:
        if st.button('Rejeitar', key='reject_pair', use_container_width=True):
            reject_pair(str(chosen))
    _render_feedback()
    render_history()


def _render_feedback() -> None:
    '''Show one-shot full width action message.'''
    message = st.session_state.get('feedback')
    if not message:
        return
    st.success(message)
    st.session_state['feedback'] = None


def _render_audit_chips(detail: pd.Series) -> None:
    '''Render dias valor score regra as compact chips.'''
    chips = st.columns(4)
    entries = [
        ('Diferença dias', detail.get('Diferença dias')),
        ('Diferença valor', format_brl(detail.get('Diferença valor'))),
        ('Score', detail.get('Score')),
        ('Regra', detail.get('Regra')),
    ]
    for pos, (label, value) in enumerate(entries):
        with chips[pos]:
            st.markdown(
                f'<div class="audit-chip"><div class="audit-chip-label">{label}</div>'
                f'<div class="audit-chip-value">{value}</div></div>',
                unsafe_allow_html=True,
            )


def render_pair_detail(row: pd.Series) -> None:
    '''Show comparison table chips and motive.'''
    statement_frame = st.session_state.get('statement_df')
    ledger_frame = st.session_state.get('ledger_df')
    display = build_match_display(pd.DataFrame([row]), statement_frame, ledger_frame, set())
    detail = display.iloc[0] if len(display) > 0 else None
    st.dataframe(build_comparison_frame(detail), use_container_width=True, hide_index=True)
    _render_audit_chips(detail)
    st.markdown(
        '<p class="body-text motivo-line"><span class="label-strong">Motivo:</span> '
        f'{_reason_label(detail.get("Motivo"))}</p>',
        unsafe_allow_html=True,
    )


def _reason_label(raw: object) -> str:
    '''Translate internal motive code to pt-BR text.'''
    labels = {
        'regra_composta_ok': 'Valor, data e descrição conferem',
        'descricao_baixa_similaridade': 'Descrição com baixa similaridade',
        'descricao_divergente': 'Descrição divergente',
        'divergencia_centavos': 'Divergência de centavos',
        'divergencia_valor_descricao': 'Valor e descrição divergentes',
        'ambiguidade_multipla': 'Múltiplos candidatos possíveis',
        'sem_candidato': 'Sem candidato próximo',
        'data_fora_tolerancia': 'Data fora da tolerância',
        'valor_fora_tolerancia': 'Valor fora da tolerância',
        'sinal_bloqueado': 'Sinal oposto (débito x crédito)',
        'duplicada_suspeita': 'Duplicada suspeita',
    }
    return labels.get(str(raw), str(raw))


def confirm_pair(pair_id: str) -> None:
    '''Mark pair manual moving to conciliadas.'''
    confirmed = set(st.session_state.get('manual_confirmed', set()))
    rejected = set(st.session_state.get('manual_rejected', set()))
    confirmed.add(pair_id)
    rejected.discard(pair_id)
    st.session_state['manual_confirmed'] = confirmed
    st.session_state['manual_rejected'] = rejected
    entry = {
        'match_id': pair_id,
        'review_action': 'conciliada_manual',
        'timestamp': datetime.now().isoformat(),
    }
    log_items = list(st.session_state.get('review_log', []))
    log_items.append(entry)
    st.session_state['review_log'] = log_items
    st.session_state['feedback'] = 'Par confirmado manualmente.'
    st.rerun()


def reject_pair(pair_id: str) -> None:
    '''Reject pair returning to pendente pool.'''
    confirmed = set(st.session_state.get('manual_confirmed', set()))
    rejected = set(st.session_state.get('manual_rejected', set()))
    rejected.add(pair_id)
    confirmed.discard(pair_id)
    st.session_state['manual_confirmed'] = confirmed
    st.session_state['manual_rejected'] = rejected
    entry = {
        'match_id': pair_id,
        'review_action': 'rejeitada',
        'timestamp': datetime.now().isoformat(),
    }
    log_items = list(st.session_state.get('review_log', []))
    log_items.append(entry)
    st.session_state['review_log'] = log_items
    st.session_state['feedback'] = 'Par rejeitado e devolvido para pendente.'
    st.rerun()


def _history_label(action: object) -> str:
    '''Translate review action to pt-BR.'''
    text = str(action)
    if text == 'conciliada_manual':
        return 'Confirmada manualmente'
    if text == 'rejeitada':
        return 'Rejeitada'
    return text


def _history_moment(raw: object) -> str:
    '''Format iso timestamp to pt-BR display.'''
    text = str(raw)
    try:
        moment = datetime.fromisoformat(text)
        return moment.strftime('%d/%m/%Y %H:%M:%S')
    except (ValueError, TypeError):
        return text


def _history_display(log_items: list) -> pd.DataFrame:
    '''Build pt-BR history frame for display.'''
    rows = []
    for item in log_items:
        rows.append(
            {
                'Par ID': item.get('match_id'),
                'Ação': _history_label(item.get('review_action')),
                'Data/Hora': _history_moment(item.get('timestamp')),
            }
        )
    return pd.DataFrame(rows, columns=['Par ID', 'Ação', 'Data/Hora'])


def render_history() -> None:
    '''Show review log with reversible action.'''
    log_items = st.session_state.get('review_log', [])
    if not log_items:
        return
    st.markdown('<p class="body-text">Histórico de revisão</p>', unsafe_allow_html=True)
    st.dataframe(_history_display(list(log_items)), use_container_width=True)
    if st.button('Desfazer última ação', key='undo_review', type='primary'):
        undo_last_review()


def undo_last_review() -> None:
    '''Revert last manual decision in session.'''
    log_items = list(st.session_state.get('review_log', []))
    if not log_items:
        return
    last = log_items.pop()
    pair_id = last.get('match_id')
    confirmed = set(st.session_state.get('manual_confirmed', set()))
    rejected = set(st.session_state.get('manual_rejected', set()))
    confirmed.discard(pair_id)
    rejected.discard(pair_id)
    st.session_state['manual_confirmed'] = confirmed
    st.session_state['manual_rejected'] = rejected
    st.session_state['review_log'] = log_items
    st.session_state['feedback'] = 'Última ação desfeita.'
    st.rerun()


def render_footer() -> None:
    '''Render parchment footer with version.'''
    st.markdown(
        f'<div class="footer"><p>Conciliação Bancária · Versão {APP_VERSION}</p></div>',
        unsafe_allow_html=True,
    )


def main() -> None:
    '''Run seven step reconciliation flow.'''
    init_state()
    load_styles()
    render_header()
    render_upload_section()
    render_params_section()
    render_concile_button()
    render_kpi_section()
    render_results_section()
    render_review_section()
    render_footer()


if __name__ == '__main__':
    main()
