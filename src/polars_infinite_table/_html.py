"""HTML rendering helpers: truncating formatter and static (non-widget) table."""

import html
import os
import re
from pathlib import Path

import polars as pl

# Private polars API; may change between polars releases.
from polars.dataframe._html import NotebookFormatter, Tag, replace_consecutive_spaces

_STATIC_CSS = (Path(__file__).parent / "static.css").read_text(encoding="utf-8")


class StrTruncatingFormatter(NotebookFormatter):
    def __init__(
        self,
        df: pl.DataFrame,
        *,
        max_cols: int = 75,
        max_rows: int = 40,
        str_len_limit: int = 30,
        from_series: bool = False,
    ):
        super().__init__(
            df, max_cols=max_cols, max_rows=max_rows, from_series=from_series
        )
        self.str_len_limit = str_len_limit

    def truncate_str(self, value: str, max_len: int) -> str:
        if len(value) <= max_len:
            return value
        return value[:max_len] + "…"

    def write_body(self) -> None:
        with Tag(self.elements, "tbody"):
            for r in self.row_idx:
                with Tag(self.elements, "tr"):
                    for c in self.col_idx:
                        with Tag(self.elements, "td"):
                            if r == -1 or c == -1:
                                self.elements.append("&hellip;")
                                continue
                            series = self.df[:, c]
                            # Truncate before escaping so entities are never split.
                            text = self.truncate_str(
                                series._s.get_fmt(r, self.str_len_limit),
                                self.str_len_limit,
                            )
                            self.elements.append(
                                replace_consecutive_spaces(html.escape(text))
                            )


def polars_repr_html(df: pl.DataFrame, *, _from_series: bool = False) -> str:
    max_cols = int(os.environ.get("POLARS_FMT_MAX_COLS", 75))
    if max_cols < 0:
        max_cols = df.width

    max_rows = int(os.environ.get("POLARS_FMT_MAX_ROWS", 10))
    if max_rows < 0:
        max_rows = df.height

    str_len_limit = int(os.environ.get("POLARS_FMT_STR_LEN", 50))

    return "".join(
        StrTruncatingFormatter(
            df,
            max_cols=max_cols,
            max_rows=max_rows,
            str_len_limit=str_len_limit,
            from_series=_from_series,
        ).render()
    )


def extract_section(html_text: str, tag: str) -> str:
    open_tag = f"<{tag}>"
    close_tag = f"</{tag}>"
    if open_tag not in html_text or close_tag not in html_text:
        return ""
    return html_text.split(open_tag, 1)[1].split(close_tag, 1)[0]


def repr_html_with_all_rows(df: pl.DataFrame) -> str:
    # Avoid row ellipses when the configured tbl_rows is smaller than the slice.
    with pl.Config(tbl_rows=max(1, len(df))):
        return polars_repr_html(df)


# JupyterLab strips <style> tags (and the `overflow` shorthand and `position`)
# from untrusted outputs, so critical styling is also applied inline using
# properties its sanitizer allows.
_HEADER_CELL_STYLE = (
    "background-color: rgba(128, 128, 128, 0.2); font-weight: bold; "
    "padding: 4px 10px; text-align: right"
)
_BODY_CELL_STYLE = "padding: 4px 10px; text-align: right"
_STRIPE_STYLE = "background-color: rgba(128, 128, 128, 0.12)"


def _inline_cell_styles(header_html: str, body_html: str) -> tuple[str, str]:
    header_html = re.sub(
        r"<(th|td)(?=[\s>])", rf'<\1 style="{_HEADER_CELL_STYLE}"', header_html
    )
    rows = body_html.split("<tr>")
    out = [rows[0]]
    for i, row in enumerate(rows[1:], start=1):
        row = re.sub(r"<td(?=[\s>])", f'<td style="{_BODY_CELL_STYLE}"', row)
        out.append(f'<tr style="{_STRIPE_STYLE}">' if i % 2 == 0 else "<tr>")
        out.append(row)
    return header_html, "".join(out)


def build_static_table_html(
    *,
    header_html: str,
    body_html: str,
    summary_html: str = "",
    max_height: str = "500px",
) -> str:
    safe_max_height = html.escape(max_height, quote=True)
    header_html, body_html = _inline_cell_styles(header_html, body_html)
    return (
        '<div class="polars-static-preview">'
        f"<style>{_STATIC_CSS}</style>"
        f'<div class="polars-static-container" style="max-height: {safe_max_height}; '
        'overflow-x: auto; overflow-y: auto; border: 1px solid #ccc">'
        f'<table class="dataframe" style="border-collapse: collapse">{header_html}<tbody>{body_html}</tbody></table>'
        "</div>"
        f"{summary_html}"
        "</div>"
    )


def summary_note(text: str) -> str:
    return (
        '<div class="polars-static-note" '
        f'style="margin-top: 6px; font-size: 12px">'
        # `color` is stripped from inline styles; the <font> attribute survives.
        f'<font color="#888">{html.escape(text)}</font></div>'
    )


def render_static_polars_table(
    df: pl.DataFrame, *, persist_rows: int = 20, max_height: str = "500px"
) -> str:
    preview_rows = max(1, int(persist_rows))
    preview_html = repr_html_with_all_rows(df.slice(0, preview_rows))
    thead_inner = extract_section(preview_html, "thead")
    tbody_inner = extract_section(preview_html, "tbody")
    if not thead_inner:
        return preview_html

    summary_html = ""
    if len(df) > preview_rows:
        summary_html = summary_note(f"Showing first {preview_rows} of {len(df)} rows")

    return build_static_table_html(
        header_html=f"<thead>{thead_inner}</thead>",
        body_html=tbody_inner,
        summary_html=summary_html,
        max_height=max_height,
    )
