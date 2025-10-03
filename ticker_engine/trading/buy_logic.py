"""
Buy logic implementation with comprehensive checks and position sizing.

Must-pass checks (in order):
1. Market/capacity: Market open, not already holding, under max positions
2. Score gate: watchlist.score >= 0.70
3. Stability: streak >= 2 OR last 2 scores >= 0.70
4. Freshness: latest score <= 30 min ago
5. Cooldown: last sell >= 3 days ago

Sizing: Risk 0.75% equity, stop at entry - 1.5*ATR14 (or -8%), cap $20k
"""

import os
import logging
import time
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Optional, Tuple, Any
import math

from app.alpaca_client import get_portfolio_status, buy_stock
from app.slack import send_message
from app import db
from app.market_api import is_market_open
from ticker_engine.factors import get_factor_data

logger = logging.getLogger(__name__)

# Configuration
MAX_CONCURRENT_POSITIONS = 10
SCORE_THRESHOLD = 0.70
STABILITY_STREAK_DAYS = 2
FRESHNESS_MINUTES = 1440  # 24 hours (was 30 minutes - too strict)
COOLDOWN_DAYS = 3
RISK_PER_TRADE_PCT = 0.75  # 0.75% of equity
STOP_LOSS_ATR_MULTIPLIER = 1.5
FALLBACK_STOP_LOSS_PCT = 8.0  # 8% if ATR unavailable
MAX_NOTIONAL = 20000  # $20k max position size
TARGET_PROFIT_PCT = 10.0  # 10% profit target
SLEEP_MS = 15000  # 15 seconds between API calls (same as orchestrator)


def is_market_open_check() -> bool:
    """Check if market is currently open."""
    try:
        return is_market_open()
    except Exception as e:
        logger.warning(f"Failed to check market status: {e}")
        # Conservative fallback: assume closed
        return False


def get_current_positions() -> List[str]:
    """Get list of currently held symbols."""
    try:
        portfolio = get_portfolio_status()
        positions = portfolio.get("positions", [])
        return [p["symbol"] for p in positions if float(p.get("qty", 0)) > 0]
    except Exception as e:
        logger.error(f"Failed to get current positions: {e}")
        return []


def get_watchlist_entry(symbol: str) -> Optional[Dict[str, Any]]:
    """Get watchlist entry for symbol."""
    if not db.is_configured():
        return None
    
    try:
        result = db.supabase.table("watchlist").select("*").eq("symbol", symbol).execute()
        return result.data[0] if result.data else None
    except Exception as e:
        logger.error(f"Failed to get watchlist entry for {symbol}: {e}")
        return None


def get_last_two_scores(symbol: str) -> List[float]:
    """Get the last 2 scores for symbol from scores table."""
    if not db.is_configured():
        return []
    
    try:
        result = db.supabase.table("scores").select("score").eq("symbol", symbol).order("scored_at", desc=True).limit(2).execute()
        return [float(row["score"]) for row in result.data] if result.data else []
    except Exception as e:
        logger.error(f"Failed to get last scores for {symbol}: {e}")
        return []


def get_last_sell_date(symbol: str) -> Optional[datetime]:
    """Get the date of last sell for symbol from trades table."""
    if not db.is_configured():
        return None
    
    try:
        # Assuming trades table exists with columns: symbol, side, executed_at
        result = db.supabase.table("trades").select("executed_at").eq("symbol", symbol).eq("side", "sell").order("executed_at", desc=True).limit(1).execute()
        if result.data:
            return datetime.fromisoformat(result.data[0]["executed_at"].replace('Z', '+00:00'))
        return None
    except Exception as e:
        logger.debug(f"No trades table or failed to get last sell for {symbol}: {e}")
        return None


def calculate_atr_stop(symbol: str, entry_price: float) -> float:
    """Calculate stop loss using ATR method."""
    try:
        factor_data = get_factor_data(symbol)
        atr = factor_data.get("atr")
        if atr and atr > 0:
            return entry_price - (STOP_LOSS_ATR_MULTIPLIER * atr)
    except Exception as e:
        logger.warning(f"Failed to get ATR for {symbol}: {e}")
    
    # Fallback to percentage-based stop
    return entry_price * (1 - FALLBACK_STOP_LOSS_PCT / 100)


def calculate_position_size(entry_price: float, stop_price: float, portfolio_value: float) -> int:
    """Calculate position size based on risk management."""
    if entry_price <= 0 or stop_price <= 0 or portfolio_value <= 0:
        return 0
    
    # Risk per trade in dollars
    risk_dollars = portfolio_value * (RISK_PER_TRADE_PCT / 100)
    
    # Per-share risk
    per_share_risk = entry_price - stop_price
    if per_share_risk <= 0:
        return 0
    
    # Calculate shares based on risk
    shares_by_risk = risk_dollars / per_share_risk
    
    # Calculate shares based on max notional
    shares_by_notional = MAX_NOTIONAL / entry_price
    
    # Take the smaller of the two
    shares = min(shares_by_risk, shares_by_notional)
    
    # Must be at least 1 share and whole number
    return max(1, int(shares))


def check_buy_conditions(symbol: str) -> Tuple[bool, str]:
    """
    Check all buy conditions for a symbol.
    
    Returns:
        (can_buy: bool, reason: str)
    """
    
    # 1. Market/capacity checks
    if not is_market_open_check():
        return False, "market_closed"
    
    current_positions = get_current_positions()
    
    if symbol in current_positions:
        return False, "already_holding"
    
    if len(current_positions) >= MAX_CONCURRENT_POSITIONS:
        return False, "max_positions_reached"
    
    # 2. Score gate
    watchlist_entry = get_watchlist_entry(symbol)
    if not watchlist_entry:
        return False, "not_in_watchlist"
    
    last_score = watchlist_entry.get("last_score")
    if not last_score or float(last_score) < SCORE_THRESHOLD:
        return False, f"score_too_low_{last_score:.3f}"
    
    # 3. Stability check
    streak_days = watchlist_entry.get("streak_days", 0)
    if streak_days >= STABILITY_STREAK_DAYS:
        stability_ok = True
        stability_reason = f"streak_{streak_days}d"
    else:
        # Check last 2 scores
        last_scores = get_last_two_scores(symbol)
        if len(last_scores) >= 2 and all(score >= SCORE_THRESHOLD for score in last_scores):
            stability_ok = True
            stability_reason = f"last2_scores_{last_scores[0]:.3f}_{last_scores[1]:.3f}"
        else:
            return False, f"stability_failed_streak{streak_days}_scores{len(last_scores)}"
    
    # 4. Freshness check
    last_rescored_at = watchlist_entry.get("last_rescored_at")
    if last_rescored_at:
        try:
            last_rescored = datetime.fromisoformat(last_rescored_at)
            if isinstance(last_rescored, str):
                last_rescored = datetime.fromisoformat(last_rescored)
            
            # Handle timezone-naive dates by assuming UTC
            if last_rescored.tzinfo is None:
                last_rescored = last_rescored.replace(tzinfo=timezone.utc)
            
            time_since = datetime.now(timezone.utc) - last_rescored
            if time_since > timedelta(minutes=FRESHNESS_MINUTES):
                return False, f"stale_score_{time_since.total_seconds()/60:.1f}min"
        except Exception as e:
            logger.warning(f"Failed to parse last_rescored_at for {symbol}: {e}")
            return False, "freshness_parse_error"
    
    # 5. Cooldown check
    last_sell = get_last_sell_date(symbol)
    if last_sell:
        days_since_sell = (datetime.now(timezone.utc) - last_sell).days
        if days_since_sell < COOLDOWN_DAYS:
            return False, f"cooldown_{days_since_sell}d"
    
    return True, f"passed_all_checks_{stability_reason}"


def execute_buy_order(symbol: str, portfolio_value: float) -> Optional[Dict[str, Any]]:
    """
    Execute buy order with proper sizing and risk management.
    
    Returns:
        Order details or None if failed
    """
    try:
        # Get current price (using factor data for consistency)
        factor_data = get_factor_data(symbol)
        entry_price = factor_data.get("close_today")
        if not entry_price or entry_price <= 0:
            logger.error(f"Failed to get current price for {symbol}")
            return None
        
        # Rate limiting after API call
        if SLEEP_MS > 0:
            time.sleep(SLEEP_MS / 1000.0)
        
        # Calculate stop price
        stop_price = calculate_atr_stop(symbol, entry_price)
        
        # Calculate position size
        qty = calculate_position_size(entry_price, stop_price, portfolio_value)
        if qty <= 0:
            logger.error(f"Invalid quantity calculated for {symbol}: {qty}")
            return None
        
        # Calculate target price
        target_price = entry_price * (1 + TARGET_PROFIT_PCT / 100)
        
        # Execute buy order
        order = buy_stock(symbol, qty)
        
        # Prepare order details
        order_details = {
            "symbol": symbol,
            "qty": qty,
            "entry_price": entry_price,
            "stop_price": round(stop_price, 2),
            "target_price": round(target_price, 2),
            "reason": "score_entry",
            "order_id": getattr(order, 'id', str(order)),
            "notional": qty * entry_price
        }
        
        return order_details
        
    except Exception as e:
        logger.error(f"Failed to execute buy order for {symbol}: {e}")
        return None


def log_trade_to_db(order_details: Dict[str, Any]) -> None:
    """Log trade details to database."""
    if not db.is_configured():
        return
    
    try:
        trade_data = {
            "symbol": order_details["symbol"],
            "side": "buy",
            "qty": order_details["qty"],
            "price": order_details["entry_price"],
            "order_id": order_details["order_id"],
            "executed_at": datetime.now(timezone.utc).isoformat(),
            "reason": order_details["reason"],
            "stop_price": order_details["stop_price"],
            "target_price": order_details["target_price"]
        }
        
        db.supabase.table("trades").insert(trade_data).execute()
        logger.info(f"Logged trade to database: {order_details['symbol']}")
        
    except Exception as e:
        logger.error(f"Failed to log trade to database: {e}")


def check_buy_opportunities() -> List[Dict[str, Any]]:
    """
    Check all watchlist entries for buy opportunities.
    
    Returns:
        List of executed buy orders
    """
    if not db.is_configured():
        logger.warning("Database not configured, skipping buy checks")
        return []
    
    # Get portfolio value for sizing
    try:
        portfolio = get_portfolio_status()
        portfolio_value = float(portfolio["account"]["portfolio_value"])
    except Exception as e:
        logger.error(f"Failed to get portfolio value: {e}")
        return []
    
    executed_orders = []
    
    try:
        # Get all watchlist entries
        result = db.supabase.table("watchlist").select("*").execute()
        watchlist = result.data or []
        
        logger.info(f"Checking {len(watchlist)} watchlist entries for buy opportunities")
        
        for i, entry in enumerate(watchlist):
            symbol = entry["symbol"]
            
            # Check buy conditions
            can_buy, reason = check_buy_conditions(symbol)
            
            if can_buy:
                logger.info(f"✅ Buy signal for {symbol}: {reason}")
                
                # Execute buy order
                order_details = execute_buy_order(symbol, portfolio_value)
                
                if order_details:
                    executed_orders.append(order_details)
                    
                    # Log to database
                    log_trade_to_db(order_details)
                    
                    # Send Slack notification
                    message = (
                        f"🟢 BUY {order_details['qty']} {symbol} @ ${order_details['entry_price']:.2f}\n"
                        f"Stop: ${order_details['stop_price']:.2f} | Target: ${order_details['target_price']:.2f}\n"
                        f"Notional: ${order_details['notional']:.0f} | Reason: {reason}\n"
                        f"Order: {order_details['order_id']}"
                    )
                    send_message("#notifier", message)
                    
                else:
                    send_message("#notifier", f"❌ Failed to execute buy order for {symbol}")
                    
            else:
                logger.debug(f"❌ {symbol}: {reason}")
            
            # Progress logging every 10 symbols
            if (i + 1) % 10 == 0:
                logger.info(f"Processed {i + 1}/{len(watchlist)} watchlist entries...")
            
            # Progress logging every 10 symbols
            if (i + 1) % 10 == 0:
                logger.info(f"Processed {i + 1}/{len(watchlist)} watchlist entries...")
    
    except Exception as e:
        logger.error(f"Error in check_buy_opportunities: {e}")
        send_message("#notifier", f"❌ Buy logic error: {str(e)}")
    
    return executed_orders


if __name__ == "__main__":
    # Quick test
    logging.basicConfig(level=logging.INFO)
    orders = check_buy_opportunities()
    print(f"Executed {len(orders)} buy orders")
