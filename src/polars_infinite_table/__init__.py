from ._display import disable, enable
from ._widget import PolarsInfiniteTable

__all__ = ["PolarsInfiniteTable", "enable", "disable"]
__version__ = "0.1.0"


def load_ipython_extension(ipython):
    """Enable with `%load_ext polars_infinite_table`."""
    enable()


def unload_ipython_extension(ipython):
    disable()
