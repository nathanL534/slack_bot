#!/usr/bin/env python3
"""
Test script for the daily orchestrator.

This script demonstrates how to run the orchestrator and shows what it would do
without actually modifying the database (dry-run mode).
"""

import logging
from ticker_engine.orchestrator import (
    orchestrate_daily, 
    load_watchlist, 
    get_tech_universe,
    build_priority_queue,
    ADD_THRESHOLD,
    DROP_THRESHOLD,
    QUEUE_MAX
)

def test_orchestrator_components():
    """Test individual orchestrator components."""
    print("🧪 Testing orchestrator components...")
    
    # Test loading data
    print(f"\n1. Loading data sources...")
    watchlist = load_watchlist()
    tech_universe = get_tech_universe()
    
    print(f"   - Watchlist entries: {len(watchlist)}")
    print(f"   - Tech universe symbols: {len(tech_universe)}")
    
    if watchlist:
        print(f"   - Sample watchlist entry: {watchlist[0]}")
    
    # Test priority queue building
    print(f"\n2. Building priority queue...")
    priority_queue = build_priority_queue(watchlist, tech_universe[:20])  # Limit for testing
    
    print(f"   - Queue size: {len(priority_queue)} (max: {QUEUE_MAX})")
    print(f"   - Top 3 priorities: {priority_queue[:3]}")
    
    # Test configuration
    print(f"\n3. Configuration:")
    print(f"   - ADD_THRESHOLD: {ADD_THRESHOLD}")
    print(f"   - DROP_THRESHOLD: {DROP_THRESHOLD}")
    print(f"   - QUEUE_MAX: {QUEUE_MAX}")
    
    print("✅ Component tests completed")


def dry_run_orchestrator():
    """Run a dry version of the orchestrator (read-only)."""
    print("\n🔍 Dry-run orchestrator (read-only)...")
    
    try:
        # This would normally run the full orchestration
        # For demo purposes, we'll just show what would happen
        watchlist = load_watchlist()
        tech_universe = get_tech_universe()
        
        print(f"Would process {len(watchlist)} watchlist entries")
        print(f"Would consider {len(tech_universe)} tech universe symbols")
        print(f"Would rescore up to {QUEUE_MAX} symbols total")
        print(f"Would use thresholds: ADD={ADD_THRESHOLD}, DROP={DROP_THRESHOLD}")
        
        if watchlist:
            print(f"\nCurrent watchlist symbols: {[w['symbol'] for w in watchlist[:5]]}...")
        
        print("🔍 Dry-run completed (no database changes made)")
        
    except Exception as e:
        print(f"❌ Dry-run failed: {e}")


def main():
    """Main test function."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
    
    print("🚀 Orchestrator Test Suite")
    print("=" * 50)
    
    test_orchestrator_components()
    dry_run_orchestrator()
    
    print("\n" + "=" * 50)
    print("✅ All tests completed!")
    print("\nTo run the full orchestrator:")
    print("  python3 -c 'from ticker_engine.orchestrator import orchestrate_daily; orchestrate_daily()'")


if __name__ == "__main__":
    main()
