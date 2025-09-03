#!/usr/bin/env python3
"""
Simplified orchestrator test that works without database tables.

This version demonstrates the core functionality and posts to Slack
without requiring Supabase schema setup.
"""

import time
import logging
from datetime import datetime
from app.slack import send_message
from ticker_engine.scorer import swing_score
from app.finnhub_client import get_tech_tickers

def simple_orchestrator_test(max_symbols=10):
    """Run a simplified version of the orchestrator for testing."""
    
    print("🚀 Starting simplified orchestrator test...")
    
    # Send start message to Slack
    start_message = (
        f"🧪 **Simplified Orchestrator Test**\n"
        f"📅 Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"🎯 Testing {max_symbols} symbols from tech universe"
    )
    send_message("#notifier", start_message)
    
    try:
        # Get tech universe
        print("Fetching tech universe...")
        tech_symbols = get_tech_tickers()
        print(f"Got {len(tech_symbols)} tech symbols")
        
        # Limit for testing (API rate limits)
        test_symbols = tech_symbols[:max_symbols]
        
        # Score symbols
        scores = []
        skipped = []
        
        for i, symbol in enumerate(test_symbols):
            try:
                print(f"Scoring {symbol} ({i+1}/{len(test_symbols)})...")
                score = swing_score(symbol)
                scores.append((symbol, score))
                print(f"  {symbol}: {score:.3f}")
                
                # Rate limiting - 120ms between calls
                time.sleep(0.12)
                
            except Exception as e:
                print(f"  [skip] {symbol}: {e}")
                skipped.append(symbol)
                continue
        
        # Sort by score descending
        scores.sort(key=lambda x: x[1], reverse=True)
        
        # Get top 3
        top_3 = scores[:3]
        
        # Format results message
        if top_3:
            top_3_text = " | ".join([f"{sym} {score:.3f}" for sym, score in top_3])
            results_message = (
                f"✅ **Simplified Orchestrator Complete**\n"
                f"🔝 **Top 3:** {top_3_text}\n"
                f"> 📊 Scored: {len(scores)} symbols\n"
                f"> ⚠️ Skipped: {len(skipped)} symbols\n"
                f"> 🕐 Completed: {datetime.now().strftime('%H:%M:%S')}"
            )
        else:
            results_message = (
                f"❌ **Test Failed**\n"
                f"> No scores generated\n"
                f"> Skipped: {len(skipped)} symbols"
            )
        
        send_message("#notifier", results_message)
        
        print("✅ Test completed successfully!")
        print(f"Check your #notifier channel for results")
        
        return {
            "scores": scores,
            "skipped": skipped,
            "top_3": top_3
        }
        
    except Exception as e:
        error_message = f"❌ **Orchestrator Test Failed**\n> Error: {str(e)}"
        send_message("#notifier", error_message)
        print(f"❌ Test failed: {e}")
        raise

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    result = simple_orchestrator_test(max_symbols=8)  # Limit to avoid rate limits
    print(f"\nResults: {result}")
