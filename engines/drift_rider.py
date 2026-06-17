from config import PAIRS

class DriftRider:
    def __init__(self, candle_builder, spike_logger, ema_calculator,
                 rsi_calculator, velocity_calculator):

        self.candle_builder  = candle_builder
        self.spike_logger    = spike_logger
        self.ema             = ema_calculator
        self.rsi             = rsi_calculator
        self.velocity        = velocity_calculator

        # Track if we already entered drift after this spike
        self.drift_entered   = {pair: False for pair in PAIRS}
        self.last_spike_tick = {pair: -999 for pair in PAIRS}

        # Max ticks after spike to enter drift
        self.drift_window = 50

    def evaluate(self, pair: str):
        """
        Check if drift conditions are met after a spike.
        Returns dict with drift status and entry decision.
        """
        last_spike = self.spike_logger.get_last_spike(pair)
        ticks_since = self.spike_logger.get_ticks_since_spike(pair)

        # No spike recorded yet
        if last_spike is None:
            return self._no_signal(pair, "No spike recorded yet")

        # Already entered this drift
        if self.drift_entered[pair]:
            return self._no_signal(pair, "Already in drift trade")

        # Too many ticks since spike — drift window closed
        if ticks_since > self.drift_window:
            return self._no_signal(pair,
                f"Drift window closed ({ticks_since} ticks)")

        # Get indicator data
        closes = self.candle_builder.get_closes(pair)
        ema200 = self.ema.calculate(closes, 200)
        rsi_status = self.rsi.get_status(self.candle_builder, pair)
        vel_status = self.velocity.get_status(pair)

        current_price = self.candle_builder.get_latest_price(pair) \
                        if hasattr(self.candle_builder, 'get_latest_price') \
                        else (closes[-1] if closes else None)

        # Determine drift direction (opposite to spike)
        spike_direction = last_spike["direction"]
        if spike_direction == "DOWN":
            drift_direction = "BUY"   # Crash spike → buy the drift up
        else:
            drift_direction = "SELL"  # Boom spike  → sell the drift down

        # Check EMA 200 confirmation
        ema_confirms = False
        if ema200 and current_price:
            if drift_direction == "BUY" and current_price < ema200:
                ema_confirms = True  # Price below EMA200 → drift up likely
            elif drift_direction == "SELL" and current_price > ema200:
                ema_confirms = True  # Price above EMA200 → drift down likely
            else:
                ema_confirms = True  # If EMA200 not loaded yet, allow trade

        # RSI returning from extreme (not yet at midpoint 50)
        rsi_val = rsi_status["rsi"]
        rsi_confirms = False
        if rsi_val is None:
            rsi_confirms = True  # Not enough data yet — allow
        elif drift_direction == "BUY" and rsi_val < 50:
            rsi_confirms = True  # RSI returning upward from oversold
        elif drift_direction == "SELL" and rsi_val > 50:
            rsi_confirms = True  # RSI returning downward from overbought

        # Velocity steady (not compressing — no new spike loading)
        vel_ratio = vel_status["compression_ratio"]
        velocity_steady = True
        if vel_ratio and vel_ratio < 0.4:
            velocity_steady = False  # Compression forming — abort drift

        # All 4 conditions
        conditions = {
            "C1_spike_recent":   ticks_since <= self.drift_window,
            "C2_ema_confirms":   ema_confirms,
            "C3_rsi_confirms":   rsi_confirms,
            "C4_velocity_steady": velocity_steady
        }

        all_met = all(conditions.values())

        return {
            "pair":            pair,
            "should_enter":    all_met,
            "direction":       drift_direction,
            "conditions":      conditions,
            "ticks_since_spike": ticks_since,
            "spike_size":      last_spike["move_size"],
            "spike_direction": spike_direction,
            "rsi":             rsi_val,
            "ema200":          ema200,
            "vel_ratio":       vel_ratio,
            "reason":          "All conditions met" if all_met
                               else "Conditions not met"
        }

    def _no_signal(self, pair: str, reason: str):
        return {
            "pair":         pair,
            "should_enter": False,
            "direction":    None,
            "conditions":   {},
            "reason":       reason
        }

    def confirm_entry(self, pair: str):
        """Call this when drift trade is actually opened"""
        self.drift_entered[pair] = True
        print(f"[DRIFT RIDER] Entry confirmed on {pair}")

    def reset_after_spike(self, pair: str):
        """
        Call this when a NEW spike is detected.
        Resets drift state so we can enter drift again.
        """
        self.drift_entered[pair] = False
        print(f"[DRIFT RIDER] Reset for {pair} — "
              f"new spike detected, drift window open")