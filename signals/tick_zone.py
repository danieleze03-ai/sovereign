from config import PAIRS, INDEX_AVERAGES, TICK_ZONE_PCT

class TickZoneDetector:
    def __init__(self):
        pass

    def is_in_zone(self, pair: str, ticks_since_spike: int):
        """
        Returns True if we are past 60% of the index average
        since the last spike — elevated probability zone.

        Crash 500: zone activates at tick 300+
        Boom  500: zone activates at tick 300+
        Crash1000: zone activates at tick 600+
        Boom 1000: zone activates at tick 600+
        """
        average = INDEX_AVERAGES[pair]
        zone_start = int(average * TICK_ZONE_PCT)
        return ticks_since_spike >= zone_start

    def get_zone_progress(self, pair: str, ticks_since_spike: int):
        """
        Returns progress as percentage toward spike zone.
        0% = just had a spike
        100% = at zone threshold
        150%+ = well past average (very high probability)
        """
        average = INDEX_AVERAGES[pair]
        progress = (ticks_since_spike / average) * 100
        return round(progress, 1)

    def get_status(self, pair: str, ticks_since_spike: int):
        """Return full tick zone status for a pair"""
        in_zone = self.is_in_zone(pair, ticks_since_spike)
        progress = self.get_zone_progress(pair, ticks_since_spike)
        average = INDEX_AVERAGES[pair]
        zone_start = int(average * TICK_ZONE_PCT)

        return {
            "pair":              pair,
            "ticks_since_spike": ticks_since_spike,
            "zone_start":        zone_start,
            "index_average":     average,
            "progress_pct":      progress,
            "in_zone":           in_zone,
            "signal":            in_zone
        }