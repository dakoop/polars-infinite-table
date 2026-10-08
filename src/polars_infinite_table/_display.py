import polars as pl
from IPython import get_ipython

from ._config import DISPLAY_CONFIG
from ._html import render_static_polars_table
from ._widget import PolarsInfiniteTable

_previous_html_formatter = None
_previous_mimebundle_formatter = None


def _html_formatter(ip):
    return ip.display_formatter.formatters["text/html"]


def _mimebundle_formatter(ip):
    return ip.display_formatter.mimebundle_formatter


def _static_repr_html(df: pl.DataFrame) -> str:
    return render_static_polars_table(
        df,
        persist_rows=DISPLAY_CONFIG["persist_rows"],
        max_height=DISPLAY_CONFIG["max_height"],
    )


def _mimebundle(df: pl.DataFrame):
    bundle = PolarsInfiniteTable(df)._repr_mimebundle_()
    if isinstance(bundle, tuple):
        data, metadata = bundle
    else:
        data, metadata = bundle, None
    data = dict(data or {})
    data["text/html"] = _static_repr_html(df)
    return data if metadata is None else (data, metadata)


def _lookup(formatter):
    try:
        return formatter.lookup_by_type(pl.DataFrame)
    except KeyError:
        return None


def enable(
    *, persist_rows: int = 20, max_height: str = "500px", chunk_size: int = 50
) -> None:
    """Use the infinite table as the default display for polars DataFrames."""
    global _previous_html_formatter, _previous_mimebundle_formatter
    ip = get_ipython()
    if ip is None:
        raise RuntimeError("IPython is required to register the Polars formatters")

    DISPLAY_CONFIG.update(
        persist_rows=persist_rows, max_height=max_height, chunk_size=chunk_size
    )
    html_formatter = _html_formatter(ip)
    mimebundle_formatter = _mimebundle_formatter(ip)

    existing = _lookup(html_formatter)
    if existing is not _static_repr_html:
        _previous_html_formatter = existing
    existing = _lookup(mimebundle_formatter)
    if existing is not _mimebundle:
        _previous_mimebundle_formatter = existing

    html_formatter.for_type(pl.DataFrame, _static_repr_html)
    mimebundle_formatter.for_type(pl.DataFrame, _mimebundle)


def disable() -> None:
    """Restore whatever formatters were registered before `enable()`."""
    global _previous_html_formatter, _previous_mimebundle_formatter
    ip = get_ipython()
    if ip is None:
        raise RuntimeError("IPython is required to unregister the Polars formatters")

    for formatter, previous in (
        (_html_formatter(ip), _previous_html_formatter),
        (_mimebundle_formatter(ip), _previous_mimebundle_formatter),
    ):
        if previous is not None:
            formatter.for_type(pl.DataFrame, previous)
        else:
            formatter.type_printers.pop(pl.DataFrame, None)

    _previous_html_formatter = None
    _previous_mimebundle_formatter = None
