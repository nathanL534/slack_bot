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
        #TODO
        pass

    def get_all(self) -> List[Ticker]:
        return sorted(self.heap, reverse=True)

    def update_score(self, symbol: str, new_score: float):
        for ticker in self.heap:
            if ticker.symbol == symbol:
                ticker.score = new_score
        heapq.heapify(self.heap)
