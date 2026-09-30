'''Params snapshot wrappers for reports.'''

from src.params import infer_params as _shared_infer_params
from src.params import params_snapshot as _shared_snapshot
from src.params import snapshot_text as _shared_snapshot_text


def _params_snapshot(params: object) -> dict:
    '''Build deterministic snapshot with app version.'''
    return _shared_snapshot(params)


def _snapshot_text(snapshot: dict) -> str:
    '''Render snapshot as single audit string.'''
    return _shared_snapshot_text(snapshot)


def _infer_params(results: dict) -> dict:
    '''Infer params snapshot from first available row.'''
    return _shared_infer_params(results)
