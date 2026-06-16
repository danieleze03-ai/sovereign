import time
from collections import deque
from config import PAIRS

class CandleBuilder:
    def __init__(self, candle_duration_seconds=60):
        """
        Builds M1 candles (60 second) from raw ticks.
        candle_duration_seconds=60 means 1 minute candles.
        """
        self.candle_duration = candle_duration_seconds

        # Completed candles per pair — keep last 200
        self.candles = {pair: deque(maxlen=200) for pair in PAIRS}

        # Current open (incomplete) candle per pair
        self.current_candle = {pair: None for pair in PAIRS}

    def process_tick(self, pair: str, tick_data: dict):
        """
        Feed a tick into the candle builder.
        Returns a completed candle dict if the candle just closed, else None.
        """
        price = tick_data["price"]
        timestamp = tick_data["timestamp"]

        current = self.current_candle[pair]

        # No open candle yet — start a new one
        if current is None:
            self.current_candle[pair] = self._new_candle(price, timestamp)
            return None

        # Check if current candle has expired
        candle_end = current["open_time"] + self.candle_duration

        if timestamp >= candle_end:
            # Close current candle
            current["close"] = price
            current["close_time"] = timestamp
            completed = dict(current)

            # Store completed candle
            self.candles[pair].append(completed)

            # Start fresh candle
            self.current_candle[pair] = self._new_candle(price, timestamp)

            return completed  # Signal that a new candle was completed

        else:
            # Update current candle
            if price > current["high"]:
                current["high"] = price
            if price < current["low"]:
                current["low"] = price
            current["close"] = price
            current["tick_count"] += 1
            return None

    def _new_candle(self, price: float, timestamp: int):
        """Create a new open candle"""
        return {
            "open": price,
            "high": price,
            "low": price,
            "close": price,
            "open_time": timestamp,
            "close_time": None,
            "tick_count": 1,
            "body_size": 0.0
        }

    def get_candles(self, pair: str, count: int = None):
        """
        Return completed candles for a pair.
        If count is specified, return last N candles.
        """
        candle_list = list(self.candles[pair])

        # Calculate body sizes
        for c in candle_list:
            c["body_size"] = abs(c["close"] - c["open"])

        if count:
            return candle_list[-count:]
        return candle_list

    def get_current_candle(self, pair: str):
        """Return the currently open (incomplete) candle"""
        return self.current_candle[pair]

    def get_candle_count(self, pair: str):
        """Return number of completed candles stored"""
        return len(self.candles[pair])

    def get_last_candle(self, pair: str):
        """Return the most recently completed candle"""
        candles = self.get_candles(pair)
        if candles:
            return candles[-1]
        return None

    def get_last_n_bodies(self, pair: str, n: int):
        """
        Return body sizes of last N completed candles.
        Used by candle shrinkage detector.
        """
        candles = self.get_candles(pair, count=n)
        return [abs(c["close"] - c["open"]) for c in candles]

    def get_closes(self, pair: str, count: int = None):
        """Return list of close prices — used by RSI, EMA calculators"""
        candles = self.get_candles(pair, count=count)
        return [c["close"] for c in candles]

    def get_highs(self, pair: str, count: int = None):
        """Return list of high prices — used by ATR calculator"""
        candles = self.get_candles(pair, count=count)
        return [c["high"] for c in candles]

    def get_lows(self, pair: str, count: int = None):
        """Return list of low prices — used by ATR calculator"""
        candles = self.get_candles(pair, count=count)
        return [c["low"] for c in candles]