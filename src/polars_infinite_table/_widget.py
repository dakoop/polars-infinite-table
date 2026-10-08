from __future__ import annotations

from pathlib import Path

import anywidget
import polars as pl
import traitlets

from ._config import DISPLAY_CONFIG
from ._html import (
    build_static_table_html,
    extract_section,
    repr_html_with_all_rows,
    summary_note,
)

_HERE = Path(__file__).parent


class PolarsInfiniteTable(anywidget.AnyWidget):
    """Scrollable Polars table that lazily loads more rows from the kernel."""

    _esm = _HERE / "widget.js"
    _css = _HERE / "widget.css"

    header_html = traitlets.Unicode("").tag(sync=True)
    static_rows_html = traitlets.Unicode("").tag(sync=True)
    new_rows_html = traitlets.Unicode("").tag(sync=True)
    new_rows_token = traitlets.Int(0).tag(sync=True)
    load_token = traitlets.Int(0).tag(sync=True)
    has_more_rows = traitlets.Bool(True).tag(sync=True)
    loaded_rows = traitlets.Int(0).tag(sync=True)
    total_rows = traitlets.Int(0).tag(sync=True)
    reverse_order = traitlets.Bool(False).tag(sync=True)
    is_initialized = traitlets.Bool(False).tag(sync=True)
    max_height = traitlets.Unicode("500px").tag(sync=True)

    def __init__(
        self,
        df: pl.DataFrame,
        chunk_size: int | None = None,
        max_height: str | None = None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.df = df
        self.chunk_size = chunk_size or DISPLAY_CONFIG["chunk_size"]
        self.max_height = max_height or DISPLAY_CONFIG["max_height"]
        self.total_rows = len(df)
        self._next_offset = 0
        self._reverse_consumed = 0

        thead_inner = extract_section(
            repr_html_with_all_rows(df.slice(0, 0)), "thead"
        )
        if thead_inner:
            self.header_html = f"<thead>{thead_inner}</thead>"

        self._reset_rows_for_direction()
        self.is_initialized = True
        self.observe(self._load_next_chunk, names=["load_token"])
        self.observe(self._on_reverse_order_change, names=["reverse_order"])

    def _preview_count(self) -> int:
        return min(len(self.df), max(0, int(DISPLAY_CONFIG["persist_rows"])))

    def _reset_rows_for_direction(self) -> None:
        preview_count = self._preview_count()
        self.new_rows_html = ""
        self.new_rows_token += 1
        if self.reverse_order:
            preview_start = max(0, len(self.df) - preview_count)
            preview_df = self.df.slice(preview_start, preview_count).reverse()
            self._reverse_consumed = preview_count
            self._next_offset = 0
        else:
            preview_df = self.df.slice(0, preview_count)
            self._next_offset = preview_count
            self._reverse_consumed = 0

        self.loaded_rows = preview_count
        self.has_more_rows = preview_count < len(self.df)

        if preview_count > 0:
            self.static_rows_html = extract_section(
                repr_html_with_all_rows(preview_df), "tbody"
            )
        else:
            self.static_rows_html = ""

    def _on_reverse_order_change(self, *_):
        self._reset_rows_for_direction()

    def _next_chunk(self) -> pl.DataFrame:
        if self.reverse_order:
            consumed = self._reverse_consumed
            chunk_len = min(self.chunk_size, len(self.df) - consumed)
            chunk_start = max(0, len(self.df) - consumed - chunk_len)
            chunk = self.df.slice(chunk_start, chunk_len).reverse()
            self._reverse_consumed += len(chunk)
            self.loaded_rows = self._reverse_consumed
            self.has_more_rows = self._reverse_consumed < len(self.df)
            return chunk

        chunk = self.df.slice(self._next_offset, self.chunk_size)
        self._next_offset += len(chunk)
        self.loaded_rows = self._next_offset
        self.has_more_rows = self._next_offset < len(self.df)
        return chunk

    def _load_next_chunk(self, *_):
        consumed = self._reverse_consumed if self.reverse_order else self._next_offset
        if consumed >= len(self.df):
            self.loaded_rows = consumed
            self.has_more_rows = False
            return

        rows_only = extract_section(
            repr_html_with_all_rows(self._next_chunk()), "tbody"
        )
        if rows_only:
            self.new_rows_html = rows_only
            self.new_rows_token += 1

    def _render_static_html(self) -> str:
        summary_html = ""
        if self.reverse_order and len(self.df) > self._reverse_consumed:
            summary_html = summary_note(
                f"Showing last {self._reverse_consumed} of {len(self.df)} rows "
                "(reverse order)"
            )
        elif len(self.df) > self._next_offset > 0:
            summary_html = summary_note(
                f"Showing first {self._next_offset} of {len(self.df)} rows"
            )
        return build_static_table_html(
            header_html=self.header_html,
            body_html=self.static_rows_html,
            summary_html=summary_html,
            max_height=self.max_height,
        )

    def _repr_mimebundle_(self, include=None, exclude=None):
        bundle = super()._repr_mimebundle_(include=include, exclude=exclude)
        if isinstance(bundle, tuple):
            data, metadata = bundle
        else:
            data, metadata = bundle, None

        data = dict(data or {})
        # Embedding state lets the widget render from saved notebooks (e.g. nbviewer).
        data["application/vnd.jupyter.widget-state+json"] = {
            "version_major": 2,
            "version_minor": 0,
            "state": {
                self.model_id: {
                    "model_name": self._model_name,
                    "model_module": self._model_module,
                    "model_module_version": self._model_module_version,
                    "state": self.get_state(drop_defaults=False),
                }
            },
        }
        data["text/html"] = self._render_static_html()
        return data if metadata is None else (data, metadata)
