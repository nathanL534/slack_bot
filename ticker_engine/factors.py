import pandas as pd
from app.market_data import get_bars_12data
import requests

from dotenv import load_dotenv

load_dotenv()
import os



### Attributes for the swing scorer



def liquidity_score(data: dict) -> float:
    """
    Scores liquidity based on volume-to-spread ratio.
    Higher volume and tighter spread = better liquidity.
    Normalized to [0, 1].
    """
    volume = data["volume"]
    spread = max(data["high"] - data["low"], 0.01)
    ratio = volume / spread
    capped = min(ratio, 1_000_000)
    return capped / 1_000_000

def rel_strength_vs_xlk(data: dict, xlk_data: dict) -> float:
    """
    Compares stock's 20-day return vs XLK.
    Returns normalized relative strength score [0, 1].
    """
    stock_ret = (data["close_today"] / data["close_20d_ago"]) - 1
    xlk_ret = (xlk_data["close_today"] / xlk_data["close_20d_ago"]) - 1
    rel = (stock_ret / (xlk_ret + 1e-6)) - 1
    capped = max(min(rel, 0.5), -0.5)
    return (capped + 0.5) / 1.0



def atr_volatility_score(ohlc_data: list[dict]) -> float:
    """
    Scores ATR-based volatility relative to current price.
    More movement = better swing potential.
    Normalized to [0, 1] with max at 5% ATR.
    """
    import pandas as pd
    df = pd.DataFrame(ohlc_data)
    high_low = df["High"] - df["Low"]
    high_close = (df["High"] - df["Close"].shift()).abs()
    low_close = (df["Low"] - df["Close"].shift()).abs()
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    atr = tr.rolling(window=14).mean().iloc[-1]
    rel_atr = atr / df["Close"].iloc[-1]
    return min(rel_atr, 0.05) / 0.05


def momentum_score(close_today: float, close_20d_ago: float) -> float:
    """
    Scores momentum based on 20-day price change.
    Capped at ±10%, normalized to [0, 1].
    """
    momentum = (close_today - close_20d_ago) / close_20d_ago
    capped = max(min(momentum, 0.10), -0.10)
    return (capped + 0.10) / 0.20


def technical_flag_score(ema_50: float, ema_200: float) -> float:
    """
    Returns 1.0 if EMA50 > EMA200 (bullish crossover), else 0.0.
    """
    return 1.0 if ema_50 > ema_200 else 0.0



def technical_flag_score(ema_50: float, ema_200: float) -> float:
    """
    Returns 1.0 if EMA50 > EMA200 (bullish crossover), else 0.0.
    """
    return 1.0 if ema_50 > ema_200 else 0.0


def rsi_score(rsi: float) -> float:
    """
    Scores RSI. Oversold (<30) = high score.
    Normalized to [0, 1] with peak around RSI=30–50.
    """
    if rsi < 30:
        return 1.0
    elif rsi > 70:
        return 0.0
    else:
        return 1 - abs(rsi - 50) / 20


def compute_rsi(close_series: pd.Series, period: int = 14) -> pd.Series:
    """
    Computes the Relative Strength Index (RSI) for a given series of closing prices.
    
    RSI is a momentum oscillator that measures the speed and magnitude of recent price changes.
    Values below 30 indicate oversold conditions; above 70 indicate overbought.
    
    Args:
        close_series (pd.Series): Series of closing prices.
        period (int): Lookback period (default is 14 days).
    
    Returns:
        pd.Series: RSI values corresponding to the input series.
    """
    delta = close_series.diff()
    gain = delta.clip(lower=0).rolling(window=period).mean()
    loss = -delta.clip(upper=0).rolling(window=period).mean()
    rs = gain / (loss + 1e-6)
    return 100 - (100 / (1 + rs))

def compute_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """
    Computes the Average True Range (ATR) for a DataFrame of OHLC data.

    ATR measures volatility by taking the average of true ranges over a period.
    True range is the greatest of: 
    - high - low
    - abs(high - previous close)
    - abs(low - previous close)
    
    Args:
        df (pd.DataFrame): DataFrame with columns: 'High', 'Low', 'Close'.
        period (int): Lookback period (default is 14 days).
    
    Returns:
        pd.Series: ATR values for the input data.
    """
    high_low = df["High"] - df["Low"]
    high_close = (df["High"] - df["Close"].shift()).abs()
    low_close = (df["Low"] - df["Close"].shift()).abs()
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    return tr.rolling(window=period).mean()

def get_factor_data(symbol: str) -> dict:
    """
    Fetches all required raw data for factor scoring.
    Returns a dictionary containing volume, prices, EMA, RSI, etc.
    """
    bars = get_bars_12data(symbol, limit=60)  # Use the imported function from app.market_data

    print(f"[DEBUG] Got {len(bars)} bars for {symbol}")
    if not bars or len(bars) < 30:
        raise ValueError(f"Not enough data for {symbol}")

    df = pd.DataFrame(bars)
    df = df.rename(columns={
        "o": "Open",
        "h": "High",
        "l": "Low",
        "c": "Close",
        "v": "Volume",
        "t": "Timestamp"
    })
    df = df.sort_values("Timestamp")

    # Compute indicators
    df["ema50"] = df["Close"].ewm(span=50, adjust=False).mean()
    df["ema200"] = df["Close"].ewm(span=200, adjust=False).mean()
    df["rsi"] = compute_rsi(df["Close"])
    df["atr"] = compute_atr(df)

    latest = df.iloc[-1]
    close_20d_ago = df.iloc[-20]["Close"]

    return {
        # Liquidity
        "volume": latest["Volume"],
        "high": latest["High"],
        "low": latest["Low"],

        # Momentum & Relative Strength
        "close_today": latest["Close"],
        "close_20d_ago": close_20d_ago,

        # Technicals
        "ema_50": latest["ema50"],
        "ema_200": latest["ema200"],

        # RSI
        "rsi": latest["rsi"],

        # Volatility
        "ohlc_data": df.tail(15).to_dict("records")
    }