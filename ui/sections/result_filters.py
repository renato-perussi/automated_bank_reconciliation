'''Shared filter widgets for result tabs.'''

import pandas as pd
import streamlit as st

from src.filters import (
    filter_by_period,
    filter_by_text,
    filter_by_value,
    format_match_counter,
    format_pending_counter,
    normalize_period,
    pending_bounds,
    value_bounds,
)


def reset_match_filters(prefix: str) -> None:
    '''Clear search value filters remounting dates.'''
    epoch = int(st.session_state.get(f'{prefix}_filter_epoch', 0))
    for suffix in ['_search', '_value', '_start', '_end']:
        key = f'{prefix}{suffix}_{epoch}'
        if key in st.session_state:
            del st.session_state[key]
    st.session_state[f'{prefix}_filter_epoch'] = epoch + 1


def _reset_match_filters(prefix: str) -> None:
    '''Clear search value filters remounting dates.'''
    return reset_match_filters(prefix)


def match_period_inputs(prefix: str) -> tuple:
    '''Collect start end dates from two pickers.'''
    epoch = int(st.session_state.get(f'{prefix}_filter_epoch', 0))
    first, second = st.columns(2, gap='small')
    with first:
        raw_start = st.date_input('De', value=None, key=f'{prefix}_start_{epoch}')
    with second:
        raw_end = st.date_input('Até', value=None, key=f'{prefix}_end_{epoch}')
    return normalize_period((raw_start, raw_end))


def _match_period_inputs(prefix: str) -> tuple:
    '''Collect start end dates from two pickers.'''
    return match_period_inputs(prefix)


def filter_match_display(display: pd.DataFrame, prefix: str) -> pd.DataFrame:
    '''Apply search value period filters inside expander.'''
    total = 0 if display is None else len(display)
    box = st.expander(
        'Filtros', expanded=False, icon=':material/filter_list:', on_change='rerun',
        key=f'{prefix}_filters',
    )
    with box:
        epoch = int(st.session_state.get(f'{prefix}_filter_epoch', 0))
        low, high = value_bounds(display)
        query = st.text_input('Buscar descrição', key=f'{prefix}_search_{epoch}')
        filtered = filter_by_text(display, query)
        picked = st.slider('Valor', low, high, (low, high), key=f'{prefix}_value_{epoch}')
        filtered = filter_by_value(filtered, float(picked[0]), float(picked[1]))
        start, end = match_period_inputs(prefix)
        result = filter_by_period(filtered, start, end)
        st.markdown(
            f'<p class="filter-count">{format_match_counter(len(result), total)}</p>',
            unsafe_allow_html=True,
        )
        st.button(
            'Limpar filtros', key=f'{prefix}_clear', on_click=reset_match_filters, args=(prefix,)
        )
        return result


def _filter_match_display(display: pd.DataFrame, prefix: str) -> pd.DataFrame:
    '''Apply search value period filters inside expander.'''
    return filter_match_display(display, prefix)


def reset_pending_filters() -> None:
    '''Clear pending filters remounting date pickers.'''
    epoch = int(st.session_state.get('pending_filter_epoch', 0))
    for key in [
        f'pending_search_{epoch}',
        f'pending_value_{epoch}',
        f'pending_start_{epoch}',
        f'pending_end_{epoch}',
    ]:
        if key in st.session_state:
            del st.session_state[key]
    st.session_state['pending_filter_epoch'] = epoch + 1


def _reset_pending_filters() -> None:
    '''Clear pending filters remounting date pickers.'''
    return reset_pending_filters()


def pending_period_inputs() -> tuple:
    '''Collect start end dates from two pickers.'''
    epoch = int(st.session_state.get('pending_filter_epoch', 0))
    first, second = st.columns(2, gap='small')
    with first:
        raw_start = st.date_input('De', value=None, key=f'pending_start_{epoch}')
    with second:
        raw_end = st.date_input('Até', value=None, key=f'pending_end_{epoch}')
    return normalize_period((raw_start, raw_end))


def _pending_period_inputs() -> tuple:
    '''Collect start end dates from two pickers.'''
    return pending_period_inputs()


def filter_pending_sides(left_base: pd.DataFrame, right_base: pd.DataFrame) -> tuple:
    '''Apply pending search value period inside expander.'''
    left_total = 0 if left_base is None else len(left_base)
    right_total = 0 if right_base is None else len(right_base)
    box = st.expander(
        'Filtros', expanded=False, icon=':material/filter_list:', on_change='rerun',
        key='pending_filters',
    )
    with box:
        epoch = int(st.session_state.get('pending_filter_epoch', 0))
        low, high = pending_bounds(left_base, right_base)
        query = st.text_input('Buscar descrição', key=f'pending_search_{epoch}')
        left_filtered = filter_by_text(left_base, query)
        right_filtered = filter_by_text(right_base, query)
        picked = st.slider('Valor', low, high, (low, high), key=f'pending_value_{epoch}')
        left_out = filter_by_value(left_filtered, float(picked[0]), float(picked[1]))
        right_out = filter_by_value(right_filtered, float(picked[0]), float(picked[1]))
        start, end = pending_period_inputs()
        left_out = filter_by_period(left_out, start, end)
        right_out = filter_by_period(right_out, start, end)
        counter = format_pending_counter(len(left_out), len(right_out), left_total, right_total)
        st.markdown(f'<p class="filter-count">{counter}</p>', unsafe_allow_html=True)
        st.button('Limpar filtros', key='pending_clear', on_click=reset_pending_filters)
        return (left_out, right_out)


def _filter_pending_sides(left_base: pd.DataFrame, right_base: pd.DataFrame) -> tuple:
    '''Apply pending search value period inside expander.'''
    return filter_pending_sides(left_base, right_base)
