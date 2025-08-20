"""Market data package.

This package exposes a stable `get_bars_12data(symbol, limit=60)` function
and keeps Twelve Data specific code in `twelvedata.py`.
"""
from .twelvedata import get_bars_12data

__all__ = ["get_bars_12data"]
