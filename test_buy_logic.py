#!/usr/bin/env python3

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ticker_engine.trading.buy_logic import check_buy_opportunities, check_buy_conditions
from app.market_api import is_market_open
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def test_market_status():
    print("🕐 Market Status Check:")
    is_open = is_market_open()
    print(f"  Market is {'OPEN' if is_open else 'CLOSED'}")
    return is_open


def test_individual_symbol(symbol: str):
    print(f"\n📊 Checking {symbol}:")
    
    can_buy, reason = check_buy_conditions(symbol)
    status = "✅ BUY SIGNAL" if can_buy else "❌ NO BUY"
    print(f"  {status}: {reason}")
    
    return can_buy


def test_buy_opportunities():
    print("\n🔍 Checking All Buy Opportunities:")
    
    try:
        orders = check_buy_opportunities()
        if orders:
            print(f"  Executed {len(orders)} buy orders:")
            for order in orders:
                print(f"    🟢 {order['symbol']}: {order['qty']} shares @ ${order['entry_price']:.2f}")
        else:
            print("  No buy opportunities found")
        
        return orders
        
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return []


if __name__ == "__main__":
    print("🚀 Buy Logic Test Suite")
    print("=" * 50)
    
    # Test market status
    is_open = test_market_status()
    
    # Test a few individual symbols
    test_symbols = ["AAPL", "MSFT", "GOOGL", "TSLA"]
    for symbol in test_symbols:
        test_individual_symbol(symbol)
    
    # Only run full test if market is open (to avoid unnecessary API calls)
    if is_open:
        print("\n" + "=" * 50)
        test_buy_opportunities()
    else:
        print("\n⚠️  Skipping full test - market is closed")
    
    print("\n✅ Test complete")
