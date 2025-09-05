"""
Daily orchestrator that coordinates watchlist → priority queue → rescoring workflow.

This module handles the full daily flow:
1. Load watchlist from Supabase 
2. Build priority queue with watchlist + tech universe
3. Rescore all symbols with hysteresis logic
4. Update watchlist and insert scores to database
5. Post Slack digest with promotions/demotions and top scores
"""

import os
import time
import logging
import math
from datetime import datetime, timezone, date
from typing import Dict, List, Tuple, Optional, Any
import heapq
import requests

from app import db
from app.finnhub_client import get_tech_tickers as get_tech_universe
from ticker_engine.scorer import swing_score
from ticker_engine.ticker import Ticker

# Configuration constants
ADD_THRESHOLD = 0.57
DROP_THRESHOLD = 0.50
# ADD_THRESHOLD = 0.67
# DROP_THRESHOLD = 0.60
QUEUE_MAX = 50
TOP_N = 12
SLEEP_MS = 15000

logger = logging.getLogger(__name__)


def get_today_utc() -> str:
    """Get today's date in UTC as ISO string (YYYY-MM-DD)."""
    return datetime.now(timezone.utc).date().isoformat()


def is_valid_score(score: Any) -> bool:
    """Check if score is a valid finite number."""
    return (
        score is not None 
        and isinstance(score, (int, float)) 
        and math.isfinite(score)
    )


def upsert_watchlist(symbol: str, score: float, is_promotion: bool = False) -> None:
    """Upsert a symbol into the watchlist with updated metrics.
    
    Args:
        symbol: Ticker symbol
        score: New score value  
        is_promotion: Whether this is a new addition (promotion) from tech universe
    """
    if not db.is_configured():
        logger.warning("Supabase not configured, skipping upsert_watchlist")
        return
        
    now_utc = datetime.now(timezone.utc).isoformat()
    today_utc = get_today_utc()
    
    try:
        # Check if symbol exists in watchlist
        existing = db.supabase.table("watchlist").select("*").eq("symbol", symbol).execute()
        
        if existing.data:
            # Update existing entry
            entry = existing.data[0]
            update_data = {
                "last_score": score,
                "last_seen": now_utc,
                "last_rescored_at": today_utc,
                "below_threshold_days": 0 if score >= ADD_THRESHOLD else entry.get("below_threshold_days", 0)
            }
            
            # Only increment streak_days once per day
            if entry.get("last_rescored_at") != today_utc and score >= ADD_THRESHOLD:
                update_data["streak_days"] = entry.get("streak_days", 0) + 1
                
            db.supabase.table("watchlist").update(update_data).eq("symbol", symbol).execute()
            logger.info(f"Updated watchlist entry for {symbol}: score={score:.3f}")
            
        else:
            # Insert new entry (promotion)
            insert_data = {
                "symbol": symbol,
                "streak_days": 1 if score >= ADD_THRESHOLD else 0,
                "last_score": score,
                "last_seen": now_utc,
                "last_rescored_at": today_utc,
                "below_threshold_days": 0 if score >= ADD_THRESHOLD else 1
            }
            
            db.supabase.table("watchlist").insert(insert_data).execute()
            logger.info(f"Added new watchlist entry for {symbol}: score={score:.3f}")
            
    except Exception as e:
        logger.exception(f"Failed to upsert watchlist for {symbol}: {e}")


def load_watchlist() -> List[Dict[str, Any]]:
    """Load current watchlist from Supabase.
    
    Returns:
        List of watchlist entries with symbol, streak_days, last_score, etc.
    """
    if not db.is_configured():
        logger.warning("Supabase not configured, returning empty watchlist")
        return []
        
    try:
        result = db.supabase.table("watchlist").select("*").execute()
        return result.data or []
    except Exception as e:
        logger.exception(f"Failed to load watchlist: {e}")
        return []


def update_watchlist_below_threshold(symbol: str, score: float) -> None:
    """Update watchlist entry for symbol below DROP_THRESHOLD.
    
    Increments below_threshold_days and resets streak_days if >= 3 days.
    """
    if not db.is_configured():
        return
        
    now_utc = datetime.now(timezone.utc).isoformat()
    today_utc = get_today_utc()
    
    try:
        existing = db.supabase.table("watchlist").select("*").eq("symbol", symbol).execute()
        if not existing.data:
            return
            
        entry = existing.data[0]
        below_days = entry.get("below_threshold_days", 0) + 1
        
        update_data = {
            "last_score": score,
            "last_seen": now_utc,
            "last_rescored_at": today_utc,
            "below_threshold_days": below_days
        }
        
        # Reset streak if below threshold for 3+ days
        if below_days >= 3:
            update_data["streak_days"] = 0
            
        db.supabase.table("watchlist").update(update_data).eq("symbol", symbol).execute()
        logger.info(f"[skip] {symbol}: below threshold {below_days} days, score={score:.3f}")
        
    except Exception as e:
        logger.exception(f"Failed to update below threshold for {symbol}: {e}")


def insert_score_record(run_id: str, symbol: str, score: float) -> None:
    """Insert a score record into the scores table.
    
    Args:
        run_id: Unique identifier for this orchestrator run
        symbol: Ticker symbol
        score: Computed score value
    """
    if not db.is_configured():
        return
        
    try:
        db.supabase.table("scores").insert({
            "run_id": run_id,
            "symbol": symbol,
            "score": score,
            "scored_at": datetime.now(timezone.utc).isoformat()
        }).execute()
    except Exception as e:
        logger.exception(f"Failed to insert score for {symbol}: {e}")


def create_orchestrator_run() -> str:
    """Create a new orchestrator run record and return the run_id.
    
    Returns:
        String run_id for tracking this orchestration session
    """
    if not db.is_configured():
        return f"run_{int(time.time())}"
        
    try:
        result = db.supabase.table("orchestrator_runs").insert({
            "started_at": datetime.now(timezone.utc).isoformat(),
            "status": "running"
        }).execute()
        
        if result.data:
            return str(result.data[0]["id"])
        else:
            return f"run_{int(time.time())}"
            
    except Exception as e:
        logger.exception(f"Failed to create orchestrator run: {e}")
        return f"run_{int(time.time())}"


def update_orchestrator_run(run_id: str, status: str, summary: Optional[Dict] = None) -> None:
    """Update orchestrator run status and summary.
    
    Args:
        run_id: Run identifier
        status: New status (completed, failed, etc.)
        summary: Optional summary dictionary
    """
    if not db.is_configured():
        return
        
    try:
        update_data = {
            "status": status,
            "completed_at": datetime.now(timezone.utc).isoformat()
        }
        
        if summary:
            update_data["summary"] = summary
            
        db.supabase.table("orchestrator_runs").update(update_data).eq("id", run_id).execute()
        
    except Exception as e:
        logger.exception(f"Failed to update orchestrator run {run_id}: {e}")


def build_priority_queue(watchlist: List[Dict], tech_universe: List[str]) -> List[Tuple[Tuple, str]]:
    """Build priority queue from watchlist + tech universe with deduplication.
    
    Args:
        watchlist: List of watchlist entries from database
        tech_universe: List of symbol strings from get_tech_universe()
        
    Returns:
        List of (priority_key, symbol) tuples ready for heapq
    """
    symbol_priorities = {}
    
    # Add watchlist symbols with high priority
    for entry in watchlist:
        symbol = entry["symbol"]
        streak_days = entry.get("streak_days", 0)
        last_score = entry.get("last_score", 0.0)
        
        # Priority: (-streak_days, -last_score, symbol) for min-heap
        priority_key = (-streak_days, -last_score, symbol)
        symbol_priorities[symbol] = priority_key
    
    # Add remaining tech universe symbols with lowest baseline priority
    baseline_priority = (0, 0, "")  # Lowest priority
    for symbol in tech_universe:
        if symbol not in symbol_priorities:
            symbol_priorities[symbol] = (0, 0, symbol)
    
    # Convert to list of tuples and cap by QUEUE_MAX
    queue_items = [(priority, symbol) for symbol, priority in symbol_priorities.items()]
    heapq.heapify(queue_items)
    
    # Take top QUEUE_MAX items (min-heap, so we want the smallest/highest priority)
    result = []
    for _ in range(min(QUEUE_MAX, len(queue_items))):
        if queue_items:
            result.append(heapq.heappop(queue_items))
    
    logger.info(f"Built priority queue with {len(result)} symbols (capped at {QUEUE_MAX})")
    return result


def post_slack_digest(promotions: List[Tuple[str, float]], 
                     demotions: List[Tuple[str, float]], 
                     watchlist_top: List[Tuple[str, float]]) -> None:
    """Post daily digest to Slack using bot token.
    
    Args:
        promotions: List of (symbol, score) tuples for new additions
        demotions: List of (symbol, score) tuples for dropped symbols  
        watchlist_top: List of (symbol, score) tuples for top performers
    """
    try:
        from app.slack import send_message
        
        # Format top 3 scores
        top_3 = watchlist_top[:3]
        if len(top_3) == 0:
            top_3_text = "No watchlist entries"
        else:
            top_3_formatted = " | ".join([f"{sym} {score:.3f}" for sym, score in top_3])
            top_3_text = f"• Top {len(top_3)}: {top_3_formatted}"
        
        # Build message
        message_parts = [
            f"📊 *Daily Watchlist Update* - {get_today_utc()}",
            "",
            top_3_text
        ]
        
        if promotions:
            promo_text = ", ".join([f"{sym} ({score:.3f})" for sym, score in promotions[:5]])
            message_parts.append(f"🔼 Promotions: {promo_text}")
            
        if demotions:
            demo_text = ", ".join([f"{sym} ({score:.3f})" for sym, score in demotions[:5]])
            message_parts.append(f"🔽 Demotions: {demo_text}")
        
        message_parts.append(f"\n_Processed {len(watchlist_top)} watchlist symbols_")
        
        message_text = "\n".join(message_parts)
        
        # Send to #notifier channel
        send_message(channel="#notifier", text=message_text)
        
        logger.info("Posted daily digest to Slack")
        
    except Exception as e:
        logger.exception(f"Failed to post Slack digest: {e}")


def orchestrate_daily() -> Dict[str, Any]:
    """Coordinate the full daily watchlist → priority queue → rescoring workflow.
    
    Returns:
        Dictionary with rescored symbols, promotions, demotions, and top watchlist
    """
    logger.info("🚀 Starting daily orchestration")
    
    # Create run tracking
    run_id = create_orchestrator_run()
    logger.info(f"Created orchestrator run: {run_id}")
    
    try:
        # Load data sources
        logger.info("Loading watchlist and tech universe...")
        watchlist = load_watchlist()
        tech_universe = get_tech_universe()
        
        logger.info(f"Loaded {len(watchlist)} watchlist entries, {len(tech_universe)} tech symbols")
        
        # Build priority queue
        priority_queue = build_priority_queue(watchlist, tech_universe)
        
        # Track results
        rescored = []
        promotions = []
        demotions = []
        watchlist_symbols = {entry["symbol"] for entry in watchlist}
        today_utc = get_today_utc()
        
        # Rescore loop
        logger.info(f"Starting rescore loop for {len(priority_queue)} symbols...")
        
        for i, (priority_key, symbol) in enumerate(priority_queue):
            try:
                # Skip if already rescored today (idempotent per UTC day)
                existing_entry = next((entry for entry in watchlist if entry["symbol"] == symbol), None)
                if existing_entry and existing_entry.get("last_rescored_at") == today_utc:
                    logger.debug(f"[skip] {symbol}: already rescored today")
                    continue
                
                # Get score with error handling
                score = swing_score(symbol)
                
                if not is_valid_score(score):
                    logger.warning(f"[skip] {symbol}: invalid score {score}")
                    continue
                
                rescored.append((symbol, score))
                
                # Apply hysteresis logic
                in_watchlist = symbol in watchlist_symbols
                
                if score >= ADD_THRESHOLD:
                    # Add/update in watchlist
                    is_promotion = not in_watchlist
                    upsert_watchlist(symbol, score, is_promotion)
                    
                    if is_promotion:
                        promotions.append((symbol, score))
                        logger.info(f"🔼 Promotion: {symbol} score={score:.3f}")
                        
                elif score < DROP_THRESHOLD and in_watchlist:
                    # Handle below threshold logic
                    update_watchlist_below_threshold(symbol, score)
                    
                    # Check if this should be a demotion (3+ days below threshold)
                    updated_entry = db.supabase.table("watchlist").select("*").eq("symbol", symbol).execute()
                    if updated_entry.data and updated_entry.data[0].get("below_threshold_days", 0) >= 3:
                        demotions.append((symbol, score))
                        logger.info(f"🔽 Demotion: {symbol} score={score:.3f}")
                
                # Insert score record
                insert_score_record(run_id, symbol, score)
                
                # Rate limiting
                if SLEEP_MS > 0:
                    time.sleep(SLEEP_MS / 1000.0)
                    
                # Progress logging
                if (i + 1) % 10 == 0:
                    logger.info(f"Processed {i + 1}/{len(priority_queue)} symbols...")
                    
            except Exception as e:
                logger.error(f"[skip] {symbol}: {e}")
                continue
        
        # Get updated watchlist top performers
        updated_watchlist = load_watchlist()
        
        # Create list with (symbol, score, streak_days) tuples for proper sorting
        watchlist_entries = [
            (entry["symbol"], entry.get("last_score", 0.0), entry.get("streak_days", 0))
            for entry in updated_watchlist
        ]
        
        # Sort by streak_days desc, then score desc, then take top N symbols/scores
        watchlist_entries.sort(key=lambda x: (-x[2], -x[1]))
        watchlist_top = [(symbol, score) for symbol, score, _ in watchlist_entries[:TOP_N]]
        
        # Build result summary
        result = {
            "rescored": rescored,
            "promotions": promotions,
            "demotions": demotions,
            "watchlist_top": watchlist_top
        }
        
        # Post to Slack
        post_slack_digest(promotions, demotions, watchlist_top)
        
        # Update run status
        summary = {
            "rescored_count": len(rescored),
            "promotions_count": len(promotions),
            "demotions_count": len(demotions),
            "watchlist_size": len(updated_watchlist)
        }
        update_orchestrator_run(run_id, "completed", summary)
        
        logger.info(f"✅ Daily orchestration completed: {summary}")
        return result
        
    except Exception as e:
        logger.exception("❌ Daily orchestration failed")
        update_orchestrator_run(run_id, "failed", {"error": str(e)})
        raise


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
    result = orchestrate_daily()
    print(f"Orchestration result: {result}")
