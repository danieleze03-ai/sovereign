from signals.velocity import VelocityCalculator
from signals.candle_shrink import CandleShrinkDetector
from signals.rsi import RSICalculator
from signals.ema import EMACalculator
from signals.tick_zone import TickZoneDetector
from config import PAIRS

class SpikeCatcher:
    def __init__(self, candle_builder, spike_logger,
                 velocity, shrink, rsi, ema, tick_zone):

        self.candle_builder = candle_builder
        self.spike_logger   = spike_logger
        self.velocity       = velocity
        self.shrink         = shrink
        self.rsi            = rsi
        self.ema            = ema
        self.tick_zone      = tick_zone

        # Track last entry per pair to prevent re-entry
        self.last_entry_tick = {pair: -999 for pair in PAIRS}
        self.cooldown_ticks  = 30  # ticks between entries

    def evaluate(self, pair: str):
        """
        Run all 5 signals and return full evaluation.
        Returns dict with score, signals, and entry decision.
        """
        ticks = self.spike_logger.get_ticks_since_spike(pair)

        # Get all signal statuses
        vel_status    = self.velocity.get_status(pair)
        shrink_status = self.shrink.get_status(self.candle_builder, pair)
        rsi_status    = self.rsi.get_status(self.candle_builder, pair)
        ema_status    = self.ema.get_status(self.candle_builder, pair)
        zone_status   = self.tick_zone.get_status(pair, ticks)

        signals = {
            "S1_velocity":  vel_status["signal"],
            "S2_shrinkage": shrink_status["signal"],
            "S3_rsi":       rsi_status["signal"],
            "S4_ema":       ema_status["signal"],
            "S5_tick_zone": zone_status["signal"]
        }

        score = sum(signals.values())

        # Determine entry direction
        direction = None
        if "BOOM" in pair:
            direction = "BUY"
        elif "CRASH" in pair:
            direction = "SELL"

        # Entry requires 4/5 signals
        entry_valid = score >= 4

        # Check cooldown — don't re-enter too soon
        current_tick = self.spike_logger.get_ticks_since_spike(pair)
        last_entry   = self.last_entry_tick[pair]
        in_cooldown  = (current_tick - last_entry) < self.cooldown_ticks

        should_enter = entry_valid and not in_cooldown

        return {
            "pair":        pair,
            "score":       score,
            "signals":     signals,
            "direction":   direction,
            "entry_valid": entry_valid,
            "in_cooldown": in_cooldown,
            "should_enter": should_enter,
            "ticks_since_spike": ticks,
            "rsi_value":   rsi_status["rsi"],
            "ema_trend":   ema_status["trend"],
            "compression": vel_status["compression_ratio"],
            "zone_pct":    zone_status["progress_pct"]
        }

    def confirm_entry(self, pair: str, current_tick: int):
        """Call this when a trade is actually opened"""
        self.last_entry_tick[pair] = current_tick
        print(f"[SPIKE CATCHER] Entry confirmed on {pair} "
              f"at tick {current_tick}")

    def get_best_pair(self):
        """
        Evaluate all pairs and return the one with highest score.
        Returns (pair, evaluation) or (None, None) if no valid entry.
        """
        best_pair  = None
        best_eval  = None
        best_score = 0

        priority = ["CRASH_500", "BOOM_500", "CRASH_1000", "BOOM_1000"]

        for pair in priority:
            result = self.evaluate(pair)
            if result["should_enter"] and result["score"] > best_score:
                best_score = result["score"]
                best_pair  = pair
                best_eval  = result

        return best_pair, best_eval