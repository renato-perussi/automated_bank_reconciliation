'''Headless checks for export section helpers.'''

from src.matcher import build_params
from src.params import params_equal
from ui.sections.export_section import (
    _has_export_bytes,
    _manual_decision_count,
    _provenance_line,
    _resolve_export_params,
)


def test_params_equal_accepts_tolerance_coercions() -> None:
    '''Equal params match across decimal float str forms.'''
    base = build_params()
    twin = dict(base)
    twin['value_tolerance'] = float(base['value_tolerance'])
    assert params_equal(base, twin) is True
    text = dict(base)
    text['value_tolerance'] = str(base['value_tolerance'])
    assert params_equal(base, text) is True


def test_params_equal_rejects_changed_days_or_keys() -> None:
    '''Changed window or key set never matches.'''
    base = build_params()
    other = dict(base)
    other['date_tolerance_days'] = base['date_tolerance_days'] + 1
    assert params_equal(base, other) is False
    short = dict(base)
    del short['use_fuzzy']
    assert params_equal(base, short) is False


def test_resolve_export_params_prefers_frozen() -> None:
    '''Frozen results params drive report bytes.'''
    frozen = build_params(date_tolerance_days=5)
    session = {'params': build_params(), 'results_params': dict(frozen)}
    resolved, stale = _resolve_export_params(session)
    assert resolved == dict(frozen)
    assert stale is True


def test_resolve_export_params_clean_when_matching() -> None:
    '''Matching params resolve without stale flag.'''
    params = build_params()
    session = {'params': dict(params), 'results_params': dict(params)}
    resolved, stale = _resolve_export_params(session)
    assert resolved == dict(params)
    assert stale is False


def test_manual_decision_count_sums_both_sets() -> None:
    '''Confirmed plus rejected shape provenance caption.'''
    session = {'manual_confirmed': {'a', 'b'}, 'manual_rejected': {'c'}}
    assert _manual_decision_count(session) == 3
    assert _manual_decision_count({}) == 0


def test_provenance_line_shows_version_and_manuals() -> None:
    '''Caption carries manual total without motor version.'''
    plain = _provenance_line({})
    assert plain == ''
    assert 'Motor' not in plain
    single = _provenance_line({'manual_confirmed': {'a'}})
    assert '1 decisão manual' in single
    many = _provenance_line({'manual_confirmed': {'a'}, 'manual_rejected': {'b'}})
    assert '2 decisões manuais' in many


def test_has_export_bytes_rejects_empty() -> None:
    '''Empty payload never backs a download button.'''
    assert _has_export_bytes(b'bytes') is True
    assert _has_export_bytes(b'') is False
    assert _has_export_bytes(None) is False
