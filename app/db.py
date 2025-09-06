import os
import logging
from typing import Optional
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables from the repository root .env (if present)
# app/db.py lives in app/, so the repo root is one parent up.
repo_root = Path(__file__).resolve().parent.parent
env_path = repo_root / ".env"
if env_path.exists():
    load_dotenv(dotenv_path=str(env_path), override=False)
else:
    # fallback to default search behavior
    load_dotenv()

try:
    # Import supabase lazily; if not installed the module import will raise here
    from supabase import create_client
except Exception as e:  # pragma: no cover - keep import-time failure safe
    create_client = None  # type: ignore

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase: Optional[object] = None

if SUPABASE_URL and SUPABASE_KEY and create_client is not None:
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    except Exception as e:
        logging.warning("Failed to create Supabase client: %s", e)
        supabase = None
else:
    if not SUPABASE_URL or not SUPABASE_KEY:
        logging.info("SUPABASE_URL or SUPABASE_KEY not set; supabase client not created")


def is_configured() -> bool:
    """Return True when a Supabase client was successfully created.

    This allows importing the module in environments where env vars are not set.
    """
    return supabase is not None


def log_score(symbol: str, score: float) -> None:
    """Log or upsert a score for a ticker into Supabase.

    Raises a RuntimeError if Supabase is not configured.
    """
    if not is_configured():
        raise RuntimeError("Supabase client not configured; set SUPABASE_URL and SUPABASE_KEY")

    # make sure ticker exists
    try:
        ticker = supabase.table("tickers").select("id").eq("symbol", symbol).execute()
        if not getattr(ticker, "data", None):
            ticker = supabase.table("tickers").insert({"symbol": symbol}).execute()
        ticker_id = ticker.data[0]["id"]

        supabase.table("scores").insert({
            "ticker_id": ticker_id,
            "score": score,
        }).execute()
    except Exception as e:
        logging.exception("Failed to log score to Supabase: %s", e)
        raise



def get_latest_score(symbol):
    row = supabase.table("scores") \
                  .select("score") \
                  .eq("symbol", symbol) \
                  .order("calculated_at", desc=True) \
                  .limit(1) \
                  .execute()
    return row.data[0]["score"] if row.data else None
