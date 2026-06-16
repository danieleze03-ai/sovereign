from config import PAIRS

class CandleShrinkDetector:
    def __init__(self):
        pass

    def detect(self, candle_builder, pair: str):
        """
        Check if last 3 completed candles have progressively
        smaller bodies — signals momentum exhaustion before spike.

        Returns True if shrinkage pattern confirmed.
        """
        bodies = candle_builder.get_last_n_bodies(pair, 3)

        if len(bodies) < 3:
            return False

        # bodies[0] = oldest, bodies[2] = most recent
        # Each must be smaller than the one before it
        shrinking = (
            bodies[2] < bodies[1] and
            bodies[1] < bodies[0]
        )

        return shrinking

    def get_status(self, candle_builder, pair: str):
        """Return full shrinkage status for a pair"""
        bodies = candle_builder.get_last_n_bodies(pair, 3)
        shrinking = self.detect(candle_builder, pair)

        return {
            "pair": pair,
            "last_3_bodies": [round(b, 5) for b in bodies],
            "shrinking": shrinking,
            "signal": shrinking
        }