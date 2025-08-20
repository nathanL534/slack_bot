import os
import requests
from dotenv import load_dotenv
from datetime import datetime

from fastapi import APIRouter, HTTPException, Query

load_dotenv()

router = APIRouter()


def get_bars_12data(symbol: str, limit: int = 60, interval: str = "1day"):
    """
    Fetch OHLCV bar data from Twelve Data API and normalize output.

    Returns a list of dicts with keys: Open, High, Low, Close, Volume, Timestamp
    """
    api_key = os.getenv("TWELVE_DATA_API_KEY")
    if not api_key:
        raise RuntimeError("TWELVE_DATA_API_KEY is not set in environment")

    url = "https://api.twelvedata.com/time_series"
    params = {
        "symbol": symbol,
        "interval": interval,
        "outputsize": limit,
        "apikey": api_key
    }
    r = requests.get(url, params=params, timeout=20)
    data = r.json()

    if "values" not in data:
        raise ValueError(f"\u274c No data returned for {symbol}: {data}")

    bars = [
        {
            "Open": float(bar["open"]),
            "High": float(bar["high"]),
            "Low": float(bar["low"]),
            "Close": float(bar["close"]),
            "Volume": float(bar.get("volume", 0)),
            "Timestamp": bar.get("datetime") or bar.get("timestamp")
        }
        for bar in reversed(data["values"])  # reverse to oldest → newest
    ]
    return bars


@router.get("/api/v1/twelvedata/{symbol}")
def twelvedata_test(symbol: str, interval: str = Query("1day"), limit: int = Query(60, ge=1, le=1000)):
    """Test endpoint that returns Twelve Data bars using get_bars_12data.

    Example: /api/v1/twelvedata/AAPL?interval=1day&limit=5
    """
    try:
        bars = get_bars_12data(symbol, limit=limit, interval=interval)
        return {"symbol": symbol, "interval": interval, "limit": limit, "bars": bars}
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))
