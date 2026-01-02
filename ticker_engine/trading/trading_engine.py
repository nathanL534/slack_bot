import logging
from typing import List, Dict, Any
from datetime import datetime

from ticker_engine.trading.buy_logic import check_buy_opportunities
from ticker_engine.trading.sell_logic import check_exits
from app.slack import send_message

logger = logging.getLogger(__name__)


def run_trading_engine() -> Dict[str, Any]:
    """
    Run the complete trading engine: check for buy opportunities and sell signals.
    
    Returns:
        Dictionary with summary of actions taken
    """
    start_time = datetime.now()
    
    logger.info("🚀 Starting trading engine")
    
    # Send start notification
    send_message("#notifier", "🚀 *Trading Engine Started*")
    
    results = {
        "start_time": start_time.isoformat(),
        "buy_orders": [],
        "sell_actions": [],
        "errors": []
    }
    
    try:
        # 1. Check for buy opportunities
        logger.info("Checking buy opportunities...")
        buy_orders = check_buy_opportunities()
        results["buy_orders"] = buy_orders
        
        if buy_orders:
            logger.info(f"Executed {len(buy_orders)} buy orders")
        else:
            logger.info("No buy opportunities found")
        
        # 2. Check for sell signals
        logger.info("Checking sell signals...")
        try:
            # Note: sell_logic doesn't return actions, it executes them directly
            check_exits()
            results["sell_actions"] = ["sell_logic_executed"]  # Placeholder
            logger.info("Sell logic executed")
        except Exception as e:
            logger.error(f"Error in sell logic: {e}")
            results["errors"].append(f"sell_logic_error: {e}")
    
    except Exception as e:
        logger.error(f"Error in buy logic: {e}")
        results["errors"].append(f"buy_logic_error: {e}")
    
    # Summary
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    
    results["end_time"] = end_time.isoformat()
    results["duration_seconds"] = duration
    
    # Generate detailed diagnostic message
    detailed_summary = generate_detailed_summary(results, duration)
    
    # Send detailed notification
    send_message("#notifier", detailed_summary)
    
    logger.info(f"Trading engine complete in {duration:.1f}s")
    
    return results


def generate_detailed_summary(results: Dict[str, Any], duration: float) -> str:
    """Generate a detailed summary with diagnostics for why no trades occurred."""
    
    summary_lines = [
        "📊 *Trading Engine Complete*",
        f"⏱️ Duration: {duration:.1f}s"
    ]
    
    # Buy orders summary
    buy_count = len(results.get('buy_orders', []))
    summary_lines.append(f"🟢 Buy orders executed: {buy_count}")
    
    if buy_count > 0:
        for order in results['buy_orders']:
            summary_lines.append(f"  └─ {order['symbol']}: {order['qty']} @ ${order['entry_price']:.2f}")
    else:
        # Add diagnostic info for why no buys occurred
        try:
            from ticker_engine.trading.buy_logic import get_watchlist_entry, is_market_open_check, get_current_positions
            from app import db
            
            # Check market status
            market_open = is_market_open_check()
            summary_lines.append(f"📈 Market Status: {'OPEN' if market_open else 'CLOSED'}")
            
            if not market_open:
                summary_lines.append("  └─ ❌ Primary reason: Market closed, no buys possible")
            else:
                # Market is open, check other reasons
                current_positions = get_current_positions()
                summary_lines.append(f"💼 Current Positions: {len(current_positions)}")
                
                # Check watchlist status
                if db.is_configured():
                    result = db.supabase.table("watchlist").select("*").execute()
                    watchlist = result.data or []
                    
                    summary_lines.append(f"📋 Watchlist Entries: {len(watchlist)}")
                    
                    if len(watchlist) == 0:
                        summary_lines.append("  └─ ❌ No symbols in watchlist to buy")
                    else:
                        # Analyze top candidates
                        high_scoring = [w for w in watchlist if float(w.get('last_score', 0)) >= 0.70]
                        summary_lines.append(f"🎯 High Scoring (≥0.70): {len(high_scoring)} symbols")
                        
                        if len(high_scoring) == 0:
                            summary_lines.append("  └─ ❌ No symbols meet 0.70 score threshold")
                        else:
                            # Check freshness and other criteria
                            fresh_count = 0
                            stale_count = 0
                            from datetime import datetime, timezone, timedelta
                            
                            for entry in high_scoring[:5]:  # Check top 5
                                symbol = entry['symbol']
                                score = entry.get('last_score', 0)
                                last_updated = entry.get('last_rescored_at')
                                
                                if last_updated:
                                    try:
                                        updated_time = datetime.fromisoformat(last_updated.replace('Z', '+00:00'))
                                        if updated_time.tzinfo is None:
                                            updated_time = updated_time.replace(tzinfo=timezone.utc)
                                        minutes_old = (datetime.now(timezone.utc) - updated_time).total_seconds() / 60
                                        
                                        if minutes_old <= 30:
                                            fresh_count += 1
                                        else:
                                            stale_count += 1
                                            
                                    except:
                                        stale_count += 1
                            
                            summary_lines.append(f"🕒 Fresh Scores (<30min): {fresh_count}")
                            if stale_count > 0:
                                summary_lines.append(f"⏰ Stale Scores (>30min): {stale_count}")
                            
                            if fresh_count == 0:
                                summary_lines.append("  └─ ❌ All high-scoring symbols have stale scores")
                            else:
                                # Show top candidates that failed other checks
                                summary_lines.append("🔍 Top Candidates Analysis:")
                                for entry in high_scoring[:3]:
                                    symbol = entry['symbol']
                                    score = float(entry.get('last_score', 0))
                                    
                                    # Quick check why this symbol didn't get bought
                                    already_holding = symbol in current_positions
                                    if already_holding:
                                        reason = "already holding"
                                    else:
                                        # Could be streak, cooldown, or other factors
                                        streak = entry.get('streak_days', 0)
                                        if streak < 2:
                                            reason = f"streak only {streak}d"
                                        else:
                                            reason = "other criteria failed"
                                    
                                    summary_lines.append(f"  └─ {symbol}: {score:.3f} - {reason}")
                else:
                    summary_lines.append("  └─ ❌ Database not configured")
                    
        except Exception as e:
            summary_lines.append(f"  └─ ❌ Diagnostic error: {str(e)[:50]}")
    
    # Sell actions summary  
    sell_count = len(results.get('sell_actions', []))
    summary_lines.append(f"🔴 Sell actions: {sell_count if sell_count > 0 else 'executed'}")
    
    # Errors
    error_count = len(results.get('errors', []))
    if error_count > 0:
        summary_lines.append(f"⚠️ Errors: {error_count}")
        for error in results['errors']:
            summary_lines.append(f"  └─ {error}")
    else:
        summary_lines.append("✅ No errors")
    
    return "\n".join(summary_lines)


if __name__ == "__main__":
    # Set up logging for standalone execution
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Run the trading engine
    result = run_trading_engine()
    
    print("\n" + "="*50)
    print("TRADING ENGINE SUMMARY")
    print("="*50)
    print(f"Buy orders executed: {len(result['buy_orders'])}")
    print(f"Errors encountered: {len(result['errors'])}")
    print(f"Duration: {result['duration_seconds']:.1f} seconds")
    
    if result['buy_orders']:
        print("\nBuy Orders:")
        for order in result['buy_orders']:
            print(f"  🟢 {order['symbol']}: {order['qty']} @ ${order['entry_price']:.2f}")
    
    if result['errors']:
        print("\nErrors:")
        for error in result['errors']:
            print(f"  ❌ {error}")
