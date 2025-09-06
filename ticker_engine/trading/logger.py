

# ticker_engine/trading/logger.py

from datetime import datetime, timezone
from typing import Optional, Dict, Any

# Assumes you already expose a Supabase client somewhere in your project.
# Try to import it; or pass one in explicitly to each function via client=...
try:
    from db import supabase  # your existing global client
except Exception:
    supabase = None


# --------- helpers ---------
def _now_utc() -> datetime:
    return datetime.now(timezone.utc)

def _ensure_client(client):
    if client is not None:
        return client
    if supabase is None:
        raise RuntimeError("Supabase client not provided. Pass client=... or expose it via db.supabase")
    return supabase

def _get_ticker_id_for_symbol(client, symbol: str) -> Optional[int]:
    """Map symbol -> tickers.id (if you want to populate trades.ticker_id)."""
    res = client.table("tickers").select("id").eq("symbol", symbol).limit(1).execute()
    if res.data:
        return res.data[0]["id"]
    return None


# --------- trade logging ---------
def log_trade(
    *,
    symbol: Optional[str] = None,
    side: str,
    qty: float,
    price: Optional[float] = None,
    executed_at: Optional[datetime] = None,
    ticker_id: Optional[int] = None,
    order_info: Optional[Dict[str, Any]] = None,
    client=None,
) -> Optional[Dict[str, Any]]:
    """
    Insert a trade row. Works with your current 'trades' schema:
      id | ticker_id | side | qty | price | executed_at
    - If you only have 'symbol', we'll resolve ticker_id (if found).
    - If your 'trades' table also has extra columns (e.g., symbol, alpaca_order_id, status),
      we'll include them when present (via best-effort insert).
    Returns inserted row (dict) or None on failure.
    """
    client = _ensure_client(client)
    executed_at = executed_at or _now_utc()

    # Resolve ticker_id if not provided but symbol is known
    if ticker_id is None and symbol:
        ticker_id = _get_ticker_id_for_symbol(client, symbol)

    base_payload = {
        "ticker_id": ticker_id,
        "side": side,
        "qty": qty,
        "price": price,
        "executed_at": executed_at.isoformat(),
    }

    # Best-effort: include optional fields if your schema supports them
    extra_payload = {}
    if symbol is not None:
        extra_payload["symbol"] = symbol  # will be ignored by DB if column doesn't exist (we'll catch error)
    if order_info:
        # Common optional fields; safe to omit if your schema doesn't have them
        if "id" in order_info:
            extra_payload["alpaca_order_id"] = order_info["id"]
        if "status" in order_info:
            extra_payload["status"] = order_info["status"]
        if "filled_at" in order_info and order_info["filled_at"]:
            extra_payload["filled_at"] = (
                order_info["filled_at"].isoformat()
                if isinstance(order_info["filled_at"], datetime)
                else order_info["filled_at"]
            )

    payload = {k: v for k, v in {**base_payload, **extra_payload}.items() if v is not None}

    # Try insert with all fields; if it fails due to extra columns, retry with minimal columns
    try:
        resp = client.table("trades").insert(payload).select("*").single().execute()
        return resp.data
    except Exception:
        # Retry with minimal known schema
        minimal_payload = {k: v for k, v in base_payload.items() if v is not None}
        try:
            resp = client.table("trades").insert(minimal_payload).select("*").single().execute()
            return resp.data
        except Exception:
            return None


# --------- run logging ---------
def log_run_start(
    *,
    started_at: Optional[datetime] = None,
    status: str = "running",
    client=None,
) -> Optional[int]:
    """
    Creates an 'orchestrator_runs' row and returns its id.
    Columns present in your schema: started_at (default now), status (default 'running'), etc.
    """
    client = _ensure_client(client)
    started_at = started_at or _now_utc()
    try:
        resp = client.table("orchestrator_runs").insert(
            {"started_at": started_at.isoformat(), "status": status}
        ).select("id").single().execute()
        return resp.data["id"]
    except Exception:
        return None


def log_run_complete(
    *,
    run_id: Optional[int],
    symbols_processed: Optional[int] = None,
    promotions: Optional[int] = None,
    demotions: Optional[int] = None,
    top_performers: Optional[str] = None,
    summary: Optional[str] = None,
    status: str = "success",
    error_message: Optional[str] = None,
    completed_at: Optional[datetime] = None,
    client=None,
) -> bool:
    """
    Updates an existing 'orchestrator_runs' row at the end of the cycle.
    Safely fills whatever columns your table has.
    """
    client = _ensure_client(client)
    if run_id is None:
        return False

    completed_at = completed_at or _now_utc()
    update = {
        "completed_at": completed_at.isoformat(),
        "status": status,
    }
    if symbols_processed is not None:
        update["symbols_processed"] = symbols_processed
    if promotions is not None:
        update["promotions"] = promotions
    if demotions is not None:
        update["demotions"] = demotions
    if top_performers is not None:
        update["top_performers"] = top_performers
    if summary is not None:
        update["summary"] = summary
    if error_message is not None:
        update["error_message"] = error_message

    try:
        client.table("orchestrator_runs").update(update).eq("id", run_id).execute()
        return True
    except Exception:
        return False


def log_error_to_run(*, run_id: Optional[int], error_message: str, client=None) -> bool:
    """
    Convenience helper to attach an error to the current run.
    """
    return log_run_complete(
        run_id=run_id,
        status="error",
        error_message=error_message,
        completed_at=_now_utc(),
        client=client,
    )
