import heapq
from typing import List, Optional
from ticker_engine.ticker import Ticker

class TickerQueue:
    def __init__(self):
        self.heap: List[Ticker] = []

    def add_ticker(self, ticker: Ticker):
        heapq.heappush(self.heap, ticker)

    def pop_top(self) -> Optional[Ticker]:
        if self.heap:
            return heapq.heappop(self.heap)
        return None

    def peek_top(self) -> Optional[Ticker]:
        if self.heap:
            return self.heap[0]
        return None

    def evict_below_threshold(self, threshold: float) -> List[Ticker]:
        """Remove and return tickers whose score is below `threshold`.

        This filters the internal heap in-place and re-heapifies.
        """
        removed = [t for t in self.heap if t.score < threshold]
        self.heap = [t for t in self.heap if t.score >= threshold]
        heapq.heapify(self.heap)
        return removed

    def get_all(self) -> List[Ticker]:
        return sorted(self.heap, reverse=True)

    def update_score(self, symbol: str, new_score: float):
        for ticker in self.heap:
            if ticker.symbol == symbol:
                ticker.score = new_score
        heapq.heapify(self.heap)

    def rebuild_from_list(self, symbols: list, score_fn):
        """Build the queue from a list of symbol strings and a score function.

        score_fn should accept a symbol (str) and return a numeric score.
        """
        self.heap = []
        for s in symbols:
            try:
                score = score_fn(s)
            except Exception:
                score = 0
            heapq.heappush(self.heap, Ticker(symbol=s, score=score))

    def refresh_scores(self, score_fn):
        """Recompute scores for all tickers in the queue using score_fn.

        score_fn accepts a symbol and returns a numeric score.
        """
        for t in self.heap:
            try:
                t.score = score_fn(t.symbol)
            except Exception:
                t.score = t.score
        heapq.heapify(self.heap)
