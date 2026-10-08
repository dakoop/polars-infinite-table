import polars as pl

from polars_infinite_table._html import StrTruncatingFormatter, polars_repr_html


def test_truncate_str():
    f = StrTruncatingFormatter(pl.DataFrame({"a": ["x"]}), str_len_limit=3)
    assert f.truncate_str("abcdef", 3) == "abc…"
    assert f.truncate_str("abc", 3) == "abc"


def test_entities_not_split(monkeypatch):
    monkeypatch.setenv("POLARS_FMT_STR_LEN", "5")
    df = pl.DataFrame({"a": ['"""""""""']})
    out = polars_repr_html(df)
    assert "&quot;" in out
    assert "&quo…" not in out and "&q…" not in out
