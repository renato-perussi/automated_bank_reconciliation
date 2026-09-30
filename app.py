'''Streamlit interface for bank reconciliation flow.'''

import tempfile
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

import pandas as pd
import streamlit as st

from src.classifier import build_result_tables
from src.config import DATE_TOLERANCE_DAYS, FUZZY_THRESHOLD, VALUE_TOLERANCE
from src.loader import get_preview, load_table, validate_not_empty
from src.logger import get_logger
from src.mapping import apply_mapping, auto_map_columns, get_mapping_options
from src.matcher import build_params
from src.normalize import normalize_table
from src.report import build_conciliation_workbook, build_exceptions_csv
from src.validate import collect_errors
from ui.components import (
    build_audit_frame,
    build_column_config,
    build_comparison_frame,
    build_match_display,
    build_pending_side,
    calc_kpis,
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


def format_error_display(frame: pd.DataFrame) -> pd.DataFrame:
    '''Translate Orientação to Como corrigir for display.'''
    columns = ['Linha', 'Motivo', 'Como corrigir']
    if frame is None or len(frame) == 0:
        return pd.DataFrame(columns=columns)
    work = frame.copy()
    if 'Orientação' in list(work.columns) and 'Como corrigir' not in list(work.columns):
        work = work.rename(columns={'Orientação': 'Como corrigir'})
    for field in columns:
        if field not in list(work.columns):
            work[field] = ''
    return work[columns]


def show_preview_errors(raw_frame: pd.DataFrame, error_frame: pd.DataFrame, prefix: str) -> None:
    '''Show five row preview plus pt-BR error table.'''
    box = st.expander(
        'Prévia e erros', expanded=False, icon=':material/preview:', on_change='rerun',
        key=f'{prefix}_preview',
    )
    if box.open is False:
        return
    with box:
        st.markdown('<p class="body-text">Prévia (5 linhas)</p>', unsafe_allow_html=True)
        st.dataframe(get_preview(raw_frame, 5), hide_index=True)
        if error_frame is not None and len(error_frame) > 0:
            st.markdown('<p class="body-text">Erros encontrados</p>', unsafe_allow_html=True)
            display = format_error_display(error_frame)
            st.dataframe(display, hide_index=True, column_config=build_column_config(display))


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
    show_preview_errors(raw_frame, errors, prefix)


def render_upload_section() -> None:
    '''Render title plus two upload cards side by side.'''
    st.markdown('<h2 class="display-md">Upload dos arquivos</h2>', unsafe_allow_html=True)
    st.markdown(
        '<p class="body-text">Envie o extrato e os lançamentos internos em CSV ou Excel.</p>',
        unsafe_allow_html=True,
    )
    left_upload, right_upload = st.columns(2, gap='medium')
    with left_upload:
        with st.container(border=True):
            render_single_upload(
                'Extrato bancário (CSV ou Excel)',
                'statement',
                'statement_df',
                'statement_errors',
                'statement',
            )
    with right_upload:
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
    st.markdown('<h2 class="display-md">Parâmetros</h2>', unsafe_allow_html=True)
    date_tolerance_days = st.slider('Tolerância de dias', 0, 30, DATE_TOLERANCE_DAYS)
    st.caption('2 dias cobre compensação D+1.')
    fuzzy_threshold = st.slider('Similaridade mínima (%)', 0, 100, FUZZY_THRESHOLD)
    use_fuzzy = st.toggle('Usar similaridade de descrição', True)
    st.caption('85 equilibra precisão e revisão manual.')
    raw_tolerance = st.number_input(
        'Tolerância de valor (R$)', 0.00, 10.00, float(VALUE_TOLERANCE), step=0.01
    )
    st.caption('0,00 exige valor exato. Ex.: 0,05 permite centavos.')
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
    pressed = st.button('Conciliar', key='concile_action', type='primary', width='stretch')
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


def render_empty_results() -> None:
    '''Render placeholder keeping right panel visible.'''
    st.markdown('<h2 class="display-md">Resultados</h2>', unsafe_allow_html=True)
    with st.container(border=True):
        st.markdown(
            '<p class="body-text">Nenhum resultado ainda.</p>',
            unsafe_allow_html=True,
        )
        st.caption('Envie os dois arquivos e clique em Conciliar.')


def render_kpi_section() -> None:
    '''Render five indicators plus exception bar.'''
    results = st.session_state.get('results')
    if results is None:
        render_empty_results()
        return
    statement_frame = st.session_state.get('statement_df')
    ledger_frame = st.session_state.get('ledger_df')
    statement_count = 0 if statement_frame is None else len(statement_frame)
    ledger_count = 0 if ledger_frame is None else len(ledger_frame)
    kpis = calc_kpis(results, statement_count, ledger_count)
    kpis = _apply_manual_kpis(kpis)
    st.markdown('<h2 class="display-md">Resultados</h2>', unsafe_allow_html=True)
    with st.container(horizontal=True):
        render_kpi_card('Total extrato', str(kpis['total_statement']))
        render_kpi_card('Total interno', str(kpis['total_ledger']))
        render_kpi_card('% Conciliado', format_pct(kpis['pct_auto']))
        render_kpi_card('% Para revisão', format_pct(kpis['pct_review']))
        render_kpi_card('% Pendente', format_pct(kpis['pct_pending']))
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
    pct_divergent = round((divergent_len + dup_len) / unified * 100, 1)
    updated = dict(kpis)
    updated['pct_auto'] = float(pct_auto)
    updated['pct_review'] = float(pct_review)
    updated['pct_pending'] = float(pct_pending)
    updated['pct_divergent'] = float(pct_divergent)
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


def _filter_match_display(display: pd.DataFrame, prefix: str) -> pd.DataFrame:
    '''Apply search value period filters inside expander.'''
    box = st.expander(
        'Filtros', expanded=False, icon=':material/filter_list:', on_change='rerun',
        key=f'{prefix}_filters',
    )
    with box:
        query = st.text_input('Buscar descrição', key=f'{prefix}_search')
        filtered = filter_by_text(display, query)
        low, high = _value_bounds(filtered)
        picked = st.slider('Valor', low, high, (low, high), key=f'{prefix}_value')
        filtered = filter_by_value(filtered, float(picked[0]), float(picked[1]))
        period = st.date_input('Período', value=None, key=f'{prefix}_period')
        start, end = _normalize_period(period)
        return filter_by_period(filtered, start, end)


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
    display = _filter_match_display(display, prefix)
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


def _filter_pending_sides(left_base: pd.DataFrame, right_base: pd.DataFrame) -> tuple:
    '''Apply pending search value period inside expander.'''
    box = st.expander(
        'Filtros', expanded=False, icon=':material/filter_list:', on_change='rerun',
        key='pending_filters',
    )
    with box:
        query = st.text_input('Buscar descrição', key='pending_search')
        left_filtered = filter_by_text(left_base, query)
        right_filtered = filter_by_text(right_base, query)
        low, high = _pending_bounds(left_filtered, right_filtered)
        picked = st.slider('Valor', low, high, (low, high), key='pending_value')
        left_out = filter_by_value(left_filtered, float(picked[0]), float(picked[1]))
        right_out = filter_by_value(right_filtered, float(picked[0]), float(picked[1]))
        period = st.date_input('Período', value=None, key='pending_period')
        start, end = _normalize_period(period)
        left_out = filter_by_period(left_out, start, end)
        right_out = filter_by_period(right_out, start, end)
        return (left_out, right_out)


def render_pending_tab() -> None:
    '''Render two unmatched tables with filters.'''
    results = st.session_state.get('results')
    pending = results.get('pending') if results else pd.DataFrame()
    statement_frame = st.session_state.get('statement_df')
    ledger_frame = st.session_state.get('ledger_df')
    left_base = build_pending_side(pending, statement_frame, 'statement')
    right_base = build_pending_side(pending, ledger_frame, 'ledger')
    left_display, right_display = _filter_pending_sides(left_base, right_base)
    st.markdown('<p class="body-text">Extrato sem par</p>', unsafe_allow_html=True)
    render_status_table(left_display)
    st.markdown('<p class="body-text">Interno sem par</p>', unsafe_allow_html=True)
    render_status_table(right_display)


def render_error_tab() -> None:
    '''Render combined file error tables.'''
    statement_errors = st.session_state.get('statement_errors')
    ledger_errors = st.session_state.get('ledger_errors')
    st.markdown('<p class="body-text">Erros do extrato</p>', unsafe_allow_html=True)
    render_status_table(format_error_display(statement_errors))
    st.markdown('<p class="body-text">Erros do interno</p>', unsafe_allow_html=True)
    render_status_table(format_error_display(ledger_errors))


def _result_tab_labels() -> list:
    '''Return six pt-BR tab labels with icons.'''
    return [
        ':material/check_circle: Conciliadas',
        ':material/rate_review: Para revisão',
        ':material/pending: Pendentes',
        ':material/warning: Divergentes',
        ':material/content_copy: Duplicadas',
        ':material/error: Erros',
    ]


def _show_auto_tab(tab: object, results: dict) -> None:
    '''Render conciliadas content when tab open.'''
    with tab:
        if tab.open is not False:
            render_match_tab(results.get('auto'), 'auto', 'Nenhuma conciliada ainda.')


def _show_potential_tab(tab: object, results: dict) -> None:
    '''Render revision content with review panel.'''
    with tab:
        if tab.open is not False:
            render_match_tab(results.get('potential'), 'potential', 'Nenhum par para revisão.')
            render_review_section()


def _show_simple_tab(tab: object, results: dict, frame_key: str, prefix: str, empty: str) -> None:
    '''Render single match tab when open.'''
    with tab:
        if tab.open is not False:
            render_match_tab(results.get(frame_key), prefix, empty)


def render_results_section() -> None:
    '''Render six tabs with pt-BR tables.'''
    results = st.session_state.get('results')
    if results is None:
        return
    tabs = st.tabs(_result_tab_labels(), key='results_tabs', on_change='rerun')
    _show_auto_tab(tabs[0], results)
    _show_potential_tab(tabs[1], results)
    with tabs[2]:
        if tabs[2].open is not False:
            render_pending_tab()
    _show_simple_tab(tabs[3], results, 'divergent', 'divergent', 'Nenhuma divergência.')
    _show_simple_tab(tabs[4], results, 'duplicate', 'duplicate', 'Nenhuma duplicada.')
    with tabs[5]:
        if tabs[5].open is not False:
            render_error_tab()


def _filtered_review_rows(potential: object) -> object:
    '''Filter potential removing confirmed rejected pairs.'''
    confirmed = st.session_state.get('manual_confirmed', set())
    rejected = st.session_state.get('manual_rejected', set())
    blocked = set(confirmed) | set(rejected)
    if 'match_id' not in potential.columns:
        return potential
    return potential[~potential['match_id'].isin(blocked)]


def _pick_review_row(available: object) -> tuple:
    '''Select review pair returning chosen row.'''
    options = available['match_id'].astype(str).tolist()
    chosen = st.selectbox('Selecione o par para revisão', options, key='review_pick')
    row = available[available['match_id'].astype(str) == str(chosen)].iloc[0]
    return (chosen, row)


def _render_review_actions(chosen: str) -> None:
    '''Render confirm reject buttons plus feedback history.'''
    confirm_col, reject_col, _ = st.columns([1, 1, 2])
    with confirm_col:
        confirm = st.button(
            'Confirmar', key='confirm_pair', type='primary', width='stretch',
            icon=':material/check:',
        )
        if confirm:
            confirm_pair(str(chosen))
    with reject_col:
        reject = st.button(
            'Rejeitar', key='reject_pair', width='stretch', icon=':material/close:'
        )
        if reject:
            reject_pair(str(chosen))
    _render_feedback()
    render_history()


def render_review_section() -> None:
    '''Render side by side review inside revision tab.'''
    results = st.session_state.get('results')
    if results is None:
        return
    potential = results.get('potential')
    if potential is None or len(potential) == 0:
        return
    st.markdown('<div class="review-divider"></div>', unsafe_allow_html=True)
    st.markdown(
        '<p class="body-text"><span class="label-strong">Resultado lado a lado</span>'
        ' — extrato x interno</p>',
        unsafe_allow_html=True,
    )
    available = _filtered_review_rows(potential)
    if len(available) == 0:
        st.markdown(
            '<p class="body-text">Nenhum par disponível para revisão.</p>', unsafe_allow_html=True
        )
        render_history()
        return
    chosen, row = _pick_review_row(available)
    render_pair_detail(row)
    _render_review_actions(chosen)


def _render_feedback() -> None:
    '''Show one-shot full width action message.'''
    message = st.session_state.get('feedback')
    if not message:
        return
    st.success(message)
    st.session_state['feedback'] = None


def render_pair_detail(row: pd.Series) -> None:
    '''Show comparison table audit table and motive.'''
    statement_frame = st.session_state.get('statement_df')
    ledger_frame = st.session_state.get('ledger_df')
    display = build_match_display(pd.DataFrame([row]), statement_frame, ledger_frame, set())
    detail = display.iloc[0] if len(display) > 0 else None
    frame = build_comparison_frame(detail)
    st.table(frame, border='horizontal', width='content', hide_index=True)
    audit = build_audit_frame(detail)
    st.table(audit, border='horizontal', width='content', hide_index=True)
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
    display = _history_display(list(log_items))
    st.dataframe(display, hide_index=True, column_config=build_column_config(display))
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


@st.cache_data(ttl=600, max_entries=5)
def _cached_export_payloads(
    results: dict,
    params: dict,
    statement_frame: object,
    ledger_frame: object,
    statement_errors: object,
    ledger_errors: object,
    review_log: object,
) -> tuple:
    '''Build cached excel csv bytes from hashable inputs.'''
    errors = {'statement': statement_errors, 'ledger': ledger_errors}
    try:
        excel_bytes = build_conciliation_workbook(
            results, params, statement_frame, ledger_frame, errors, review_log
        )
    except (ValueError, KeyError, RuntimeError) as exc:
        logger.warning(f'Excel build failed with {exc}')
        excel_bytes = b''
    try:
        csv_bytes = build_exceptions_csv(
            results, params, statement_frame, ledger_frame, errors, review_log
        )
    except (ValueError, KeyError, RuntimeError) as exc:
        logger.warning(f'Csv build failed with {exc}')
        csv_bytes = b''
    return excel_bytes, csv_bytes


def build_export_payloads() -> tuple:
    '''Build excel csv bytes in memory without files.'''
    results = st.session_state.get('results')
    params = st.session_state.get('params', build_params())
    statement_frame = st.session_state.get('statement_df')
    ledger_frame = st.session_state.get('ledger_df')
    statement_errors = st.session_state.get('statement_errors')
    ledger_errors = st.session_state.get('ledger_errors')
    review_log = st.session_state.get('review_log', [])
    return _cached_export_payloads(
        results, params, statement_frame, ledger_frame, statement_errors, ledger_errors,
        review_log,
    )


def render_download_buttons(excel_bytes: bytes, csv_bytes: bytes) -> None:
    '''Render two side by side download actions.'''
    left, right = st.columns(2)
    with left:
        st.download_button(
            'Baixar Excel',
            data=excel_bytes,
            file_name='relatorio_conciliacao.xlsx',
            mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            key='download_excel',
            width='stretch',
            type='primary',
            icon=':material/download:',
        )
    with right:
        st.download_button(
            'Baixar CSV de exceções',
            data=csv_bytes,
            file_name='relatorio_excecoes.csv',
            mime='text/csv',
            key='download_csv',
            width='stretch',
            type='primary',
            icon=':material/download:',
        )


def render_export_section() -> None:
    '''Render centered download buttons for reports.'''
    results = st.session_state.get('results')
    if results is None:
        return
    st.divider()
    st.markdown(
        '<h2 class="display-md export-center">Exportar relatórios</h2>', unsafe_allow_html=True
    )
    st.markdown(
        '<p class="body-text export-center">Baixe o relatório completo e o CSV de exceções.</p>',
        unsafe_allow_html=True,
    )
    excel_bytes, csv_bytes = build_export_payloads()
    outer_left, outer_center, outer_right = st.columns([1, 2, 1])
    with outer_center:
        render_download_buttons(excel_bytes, csv_bytes)


def main() -> None:
    '''Run wide two column reconciliation flow.'''
    st.set_page_config(
        page_title='Conciliação Bancária', layout='wide', page_icon=':material/account_balance:'
    )
    init_state()
    load_styles()
    render_header()
    st.divider()
    left_panel, right_panel = st.columns([1, 1], gap='large')
    with left_panel:
        render_upload_section()
        render_params_section()
        render_concile_button()
    with right_panel:
        render_kpi_section()
        render_results_section()
    render_export_section()


if __name__ == '__main__':
    main()
