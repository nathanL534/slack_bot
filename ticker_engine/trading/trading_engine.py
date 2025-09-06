"""
Trading engine entry point that coordinates buy and sell logic.

This module provides the main entry points for automated trading decisions.
"""

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
    
    # Send summary notification
    summary_msg = (
        f"📊 *Trading Engine Complete*\n"
        f"🟢 Buy orders: {len(results['buy_orders'])}\n"
        f"🔴 Sell actions: executed\n"
        f"⚠️ Errors: {len(results['errors'])}\n"
        f"⏱️ Duration: {duration:.1f}s"
    )
    
    if results["errors"]:
        summary_msg += f"\n❌ Errors: {', '.join(results['errors'])}"
    
    send_message("#notifier", summary_msg)
    
    logger.info(f"Trading engine complete in {duration:.1f}s")
    
    return results


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
