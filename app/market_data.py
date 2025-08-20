"""Compatibility shim: re-export the market_data package implementation.

This file keeps older imports working (from app.market_data import get_bars_12data)
while the Twelve Data specific code lives under `app.market_data.twelvedata`.
"""
from app.market_data.twelvedata import get_bars_12data

__all__ = ["get_bars_12data"]