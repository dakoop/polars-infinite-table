# polars-infinite-table

Infinite-scrolling display for [Polars](https://pola.rs) DataFrames in Jupyter, built on [anywidget](https://anywidget.dev).

- Shows the first rows immediately and loads more from the kernel as you scroll.
- Sticky headers, optional reverse order, and a static HTML fallback (first rows only) for viewers that cannot run widgets.
- Long cell values are truncated without splitting HTML entities.

Developed with assistance from GitHub Copilot.

## Install

```sh
pip install git+https://github.com/dakoop/polars-infinite-table
```

## Usage

```python
import polars_infinite_table as pit

pit.enable(persist_rows=20, max_height="500px", chunk_size=50)  # default display for pl.DataFrame
pit.disable()                                                   # restore previous formatters

pit.PolarsInfiniteTable(df)  # use a single table explicitly
```

Or `%load_ext polars_infinite_table`. To enable in every session, add the `enable()` call to a file in `~/.ipython/profile_default/startup/`.

### Options

| Option | Default | Meaning |
| --- | --- | --- |
| `persist_rows` | 20 | Rows rendered up front and kept in the static HTML |
| `max_height` | `500px` | Height of the scroll area |
| `chunk_size` | 50 | Rows fetched per scroll request |

Environment variables `POLARS_FMT_MAX_COLS`, `POLARS_FMT_MAX_ROWS` and `POLARS_FMT_STR_LEN` (max characters per cell, default 50) are honored.

## Notes

The formatter subclasses `polars.dataframe._html.NotebookFormatter` and uses `Series._s.get_fmt`, which are private Polars APIs and may change between releases.

## Development

```sh
pixi run test   # run the tests
pixi run lab    # start JupyterLab
```
