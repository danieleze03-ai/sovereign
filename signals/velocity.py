from collections import deque
from config import PAIRS

class VelocityCalculator:
    def __init__(self):
        # Store last 20 tick moves per pair
        self.tick_moves = {pair: deque(maxlen=20) for pair in PAIRS}
        self.last_price = {pair: None for pair in PAIRS}

    def process_tick(self, pair: str, price: float):
        """
        Feed each tick price.
        Calculates the absolute move from previous tick.
        """
        if self.last_price[pair] is None:
            self.last_price[pair] = price
            return

        move = abs(price - self.last_price[pair])
        self.tick_moves[pair].append(move)
        self.last_price[pair] = price

    def get_average_move(self, pair: str, period: int):
        """Return average tick move over last N ticks"""
        moves = list(self.tick_moves[pair])
        if len(moves) < period:
            return None
        return sum(moves[-period:]) / period

    def get_compression_ratio(self, pair: str):
        """
        Compare last 5 tick moves vs last 20 tick moves.
        Ratio below 0.6 = compression = spike loading.
        Returns ratio or None if not enough data.
        """
        avg_20 = self.get_average_move(pair, 20)
        avg_5 = self.get_average_move(pair, 5)

        if avg_20 is None or avg_5 is None:
            return None
        if avg_20 == 0:
            return None

        return round(avg_5 / avg_20, 4)

    def is_compressed(self, pair: str):
        """
        Returns True if tick velocity is compressing.
        Compression ratio below 0.6 = Signal 1 FIRES.
        """
        ratio = self.get_compression_ratio(pair)
        if ratio is None:
            return False
        return ratio < 0.6

    def get_status(self, pair: str):
        """Return full velocity status for a pair"""
        ratio = self.get_compression_ratio(pair)
        compressed = self.is_compressed(pair)
        avg_5 = self.get_average_move(pair, 5)
        avg_20 = self.get_average_move(pair, 20)

        return {
            "pair": pair,
            "avg_move_5":  round(avg_5, 6) if avg_5 else None,
            "avg_move_20": round(avg_20, 6) if avg_20 else None,
            "compression_ratio": ratio,
            "compressed": compressed,
            "signal": compressed
        }