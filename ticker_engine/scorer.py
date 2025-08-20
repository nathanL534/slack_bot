

import random 
from ticker_engine.ticker import Ticker
from ticker_engine.factors import (
    liquidity_score,
    rel_strength_vs_xlk,
    atr_volatility_score,
    momentum_score,
    technical_flag_score,
    rsi_score,
    get_factor_data
)

def dummy_score(symbol):
    return round(random.uniform(0,100), 2)



def composite_score(symbol: Ticker):
    #TODO
    pass


def swing_score(symbol):
    """calculates scores for symbols that could be good for swing trading

    Accepts either a ticker symbol string or a `Ticker` instance.

    Args:
        symbol (str | Ticker): symbol string or Ticker instance
    """
    # accept either a Ticker object or a plain symbol string
    if isinstance(symbol, Ticker):
        sym = symbol.symbol
    else:
        sym = symbol

    data = get_factor_data(sym)
    xlk_data = get_factor_data("XLK")
    
    return round(
    0.38 * liquidity_score(data) +
    0.22 * rel_strength_vs_xlk(data, xlk_data) +
    0.18 * atr_volatility_score(data["ohlc_data"]) +
    0.12 * momentum_score(data["close_today"], data["close_20d_ago"]) +
    0.06 * technical_flag_score(data["ema_50"], data["ema_200"]) +
    0.04 * rsi_score(data["rsi"]),
    4
    )