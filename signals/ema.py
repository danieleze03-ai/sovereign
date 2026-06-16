from config import PAIRS

class EMACalculator:
    def calculate(self, closes: list, period: int):
        """
        Calculate EMA manually from close prices.
        Returns EMA value or None if not enough data.
        """
        if len(closes) < period:
            return None

        sma = sum(closes[:period]) / period
        multiplier = 2 / (period + 1)
        ema = sma

        for price in closes[period:]:
            ema = (price - ema) * multiplier + ema

        return round(ema, 5)

    def calculate_series(self, closes: list, period: int, count: int = 3):
        """Calculate EMA for last N points. Used to detect crossovers."""
        results = []
        for i in range(count, 0, -1):
            subset = closes[:-i] if i > 0 else closes
            ema = self.calculate(subset, period)
            if ema:
                results.append(ema)
        current = self.calculate(closes, period)
        if current:
            results.append(current)
        return results

    def is_squeeze(self, ema9: float, ema21: float):
        """
        EMA squeeze = EMA9 and EMA21 within 0.3% of each other.
        Means short-term momentum is coiling — spike about to fire.
        """
        if ema9 is None or ema21 is None:
            return False
        diff_pct = abs(ema9 - ema21) / ema21 * 100
        return diff_pct < 0.3

    def get_trend(self, closes: list, pair: str):
        """
        EMA 200 trend direction.
        Price above EMA200 = bullish bias
        Price below EMA200 = bearish bias
        """
        if not closes:
            return None
        ema200 = self.calculate(closes, 200)
        if ema200 is None:
            return None
        current_price = closes[-1]
        if current_price > ema200:
            return "BULLISH"
        else:
            return "BEARISH"

    def get_status(self, candle_builder, pair: str):
        """Return full EMA status for a pair"""
        closes = candle_builder.get_closes(pair)

        ema9   = self.calculate(closes, 9)
        ema21  = self.calculate(closes, 21)
        ema200 = self.calculate(closes, 200)
        squeeze = self.is_squeeze(ema9, ema21)
        trend   = self.get_trend(closes, pair)
        signal  = squeeze

        return {
            "pair":    pair,
            "ema9":    ema9,
            "ema21":   ema21,
            "ema200":  ema200,
            "squeeze": squeeze,
            "trend":   trend,
            "signal":  signal
        }


class ATRCalculator:
    def calculate(self, highs: list, lows: list,
                  closes: list, period: int = 14):
        """
        Calculate ATR (Average True Range) manually.
        Used for dynamic stop-loss and take-profit sizing.
        Returns ATR value or None if not enough data.
        """
        if len(highs) < period + 1:
            return None

        true_ranges = []
        for i in range(1, len(highs)):
            high       = highs[i]
            low        = lows[i]
            prev_close = closes[i - 1]

            tr = max(
                high - low,
                abs(high - prev_close),
                abs(low  - prev_close)
            )
            true_ranges.append(tr)

        if len(true_ranges) < period:
            return None

        atr = sum(true_ranges[-period:]) / period
        return round(atr, 6)