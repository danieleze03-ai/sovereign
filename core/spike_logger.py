from collections import deque
from config import PAIRS, SPIKE_THRESHOLDS, INDEX_AVERAGES

class SpikeLogger:
    def __init__(self):
        # Spike history per pair — keep last 50 spikes
        self.spike_history = {pair: deque(maxlen=50) for pair in PAIRS}

        # Last price seen per pair (to calculate move size)
        self.last_price = {pair: None for pair in PAIRS}

        # Ticks since last spike per pair
        self.ticks_since_spike = {pair: 0 for pair in PAIRS}

        # Total spikes detected per pair
        self.total_spikes = {pair: 0 for pair in PAIRS}

        # Last spike data per pair
        self.last_spike = {pair: None for pair in PAIRS}

    def process_tick(self, pair: str, tick_data: dict):
        """
        Analyze each tick for spike detection.
        Returns spike dict if spike detected, else None.
        """
        price = tick_data["price"]
        timestamp = tick_data["timestamp"]
        tick_number = tick_data["tick_number"]

        # First tick — just store price, nothing to compare yet
        if self.last_price[pair] is None:
            self.last_price[pair] = price
            return None

        # Calculate price move from last tick
        price_move = price - self.last_price[pair]
        abs_move = abs(price_move)
        threshold = SPIKE_THRESHOLDS[pair]

        # Increment tick counter
        self.ticks_since_spike[pair] += 1

        spike_detected = None

        # Check if this tick is a spike
        if abs_move >= threshold:
            direction = "UP" if price_move > 0 else "DOWN"

            # Determine if spike matches the pair type
            is_valid_spike = False

            if "BOOM" in pair and direction == "UP":
                is_valid_spike = True
            elif "CRASH" in pair and direction == "DOWN":
                is_valid_spike = True

            if is_valid_spike:
                spike_data = {
                    "pair":             pair,
                    "direction":        direction,
                    "price_before":     self.last_price[pair],
                    "price_after":      price,
                    "move_size":        abs_move,
                    "timestamp":        timestamp,
                    "tick_number":      tick_number,
                    "ticks_since_last": self.ticks_since_spike[pair],
                    "index_average":    INDEX_AVERAGES[pair]
                }

                # Log the spike
                self.spike_history[pair].append(spike_data)
                self.last_spike[pair] = spike_data
                self.total_spikes[pair] += 1

                # Reset tick counter
                self.ticks_since_spike[pair] = 0

                spike_detected = spike_data

                print(f"\n⚡ SPIKE DETECTED [{pair}]")
                print(f"   Direction:    {direction}")
                print(f"   Move Size:    {abs_move:.5f}")
                print(f"   Price Before: {self.last_price[pair]}")
                print(f"   Price After:  {price}")
                print(f"   Ticks Since Last Spike: "
                      f"{spike_data['ticks_since_last']}")
                print(f"   Total Spikes Today: {self.total_spikes[pair]}\n")

        # Update last price
        self.last_price[pair] = price

        return spike_detected

    def get_spike_history(self, pair: str):
        """Return full spike history for a pair"""
        return list(self.spike_history[pair])

    def get_last_spike(self, pair: str):
        """Return the most recent spike for a pair"""
        return self.last_spike[pair]

    def get_ticks_since_spike(self, pair: str):
        """Return how many ticks since the last spike"""
        return self.ticks_since_spike[pair]

    def get_total_spikes(self, pair: str):
        """Return total spikes detected today"""
        return self.total_spikes[pair]

    def get_average_ticks_between_spikes(self, pair: str):
        """
        Calculate average ticks between spikes from history.
        Useful for comparing against index average.
        """
        history = self.get_spike_history(pair)
        if len(history) < 2:
            return None

        intervals = [
            s["ticks_since_last"]
            for s in history
            if s["ticks_since_last"] > 0
        ]

        if not intervals:
            return None

        return sum(intervals) / len(intervals)

    def get_spike_probability(self, pair: str):
        """
        Return a probability score (0.0 to 1.0) based on
        how far we are into the expected spike interval.
        """
        ticks = self.ticks_since_spike[pair]
        average = INDEX_AVERAGES[pair]

        # Probability rises as we approach and pass the average
        probability = min(ticks / average, 1.5) / 1.5
        return round(probability, 4)

    def reset_daily(self):
        """Reset daily counters — called at midnight"""
        for pair in PAIRS:
            self.total_spikes[pair] = 0
        print("[SPIKE LOGGER] Daily counters reset.")