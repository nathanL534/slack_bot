from ticker_engine.queue import TickerQueue
from ticker_engine.ticker import Ticker
from ticker_engine.scorer import dummy_score
from app.fmp_client import get_tech_tickers


def main():
    queue = TickerQueue()

    print("Fetching tech tickers...")
    tech_tickers = get_tech_tickers()
    print(f"Fetched {len(tech_tickers)} tickers.\n")

    print("Scoring and queuing tickers...")
    for symbol in tech_tickers:
        score = dummy_score(symbol)
        ticker = Ticker(symbol=symbol, score=score)
        queue.add_ticker(ticker)

    print("\nTop 10 tickers by score:")
    for t in queue.get_all()[:100]:
        print(f"{t.symbol}: {t.score}")


if __name__ == "__main__":
    main()
