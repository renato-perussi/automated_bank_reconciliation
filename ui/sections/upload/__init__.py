'''Upload cards facade preserving legacy imports.'''

from ui.sections.upload.file_io import fetch_raw_table, save_temp_file
from ui.sections.upload.mapping_ui import (
    _default_index,
    _mapping_complete,
    choose_mapping,
    finalize_source,
)
from ui.sections.upload.preview_ui import (
    _build_preview_display,
    _render_source_status,
    format_error_display,
    show_preview_errors,
)
from ui.sections.upload.section import render_single_upload, render_upload_section

__all__ = [
    '_build_preview_display',
    '_default_index',
    '_mapping_complete',
    '_render_source_status',
    'choose_mapping',
    'fetch_raw_table',
    'finalize_source',
    'format_error_display',
    'render_single_upload',
    'render_upload_section',
    'save_temp_file',
    'show_preview_errors',
]
