from config import PAIRS

class RSICalculator:
    def __init__(self, period=14):
        self.period = period

    def calculate(self, closes: list):
        """
        Calculate RSI from a list of close prices.
        Built manually — no pandas-ta needed.
        Returns RSI value (0-100) or None if not enough data.
        """
        if len(closes) < self.period + 1:
            return None

        # Use only the last (period + 1) closes
        closes = closes[-(self.period + 1):]

        gains = []
        losses = []

        for i in range(1, len(closes)):
            change = closes[i] - closes[i - 1]
            if change > 0:
                gains.append(change)
                losses.append(0)
            else:
                gains.append(0)
                losses.append(abs(change))

        avg_gain = sum(gains) / self.period
        avg_loss = sum(losses) / self.period

        if avg_loss == 0:
            return 100.0

        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        return round(rsi, 2)

    def calculate_series(self, closes: list, count: int = 5):
        """
        Calculate RSI for last N periods.
        Used to detect flatline.
        Returns list of RSI values.
        """
        results = []
        min_needed = self.period + 1

        for i in range(count):
            end = len(closes) - i
            if end < min_needed:
                break
            rsi = self.calculate(closes[:end])
            if rsi is not None:
                results.append(rsi)

        results.reverse()
        return results

    def is_extreme(self, rsi: float, pair: str):
        """
        RSI extreme zones:
        Crash pairs: above 75 = overbought = crash incoming
        Boom pairs:  below 25 = oversold  = boom incoming
        """
        if rsi is None:
            return False

        if "CRASH" in pair:
            return rsi > 75
        elif "BOOM" in pair:
            return rsi < 25
        return False

    def is_flatline(self, rsi_series: list):
        """
        RSI flatline = RSI moved less than 1.5 points
        across last 4 readings.
        Means momentum is exhausted — spike is loading.
        """
        if len(rsi_series) < 4:
            return False

        last_4 = rsi_series[-4:]
        rsi_range = max(last_4) - min(last_4)
        return rsi_range < 1.5

    def get_status(self, candle_builder, pair: str):
        """Return full RSI status for a pair"""
        closes = candle_builder.get_closes(pair)

        if len(closes) < self.period + 1:
            return {
                "pair": pair,
                "rsi": None,
                "extreme": False,
                "flatline": False,
                "signal": False
            }

        rsi_series = self.calculate_series(closes, count=5)
        current_rsi = rsi_series[-1] if rsi_series else None
        extreme = self.is_extreme(current_rsi, pair)
        flatline = self.is_flatline(rsi_series)
        signal = extreme and flatline

        return {
            "pair":       pair,
            "rsi":        current_rsi,
            "rsi_series": rsi_series,
            "extreme":    extreme,
            "flatline":   flatline,
            "signal":     signal
        }