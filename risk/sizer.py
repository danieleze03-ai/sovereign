from config import RISK_PER_TRADE_PCT

class PositionSizer:
    def __init__(self):
        pass

    def calculate(self, balance: float, atr: float):
        """
        Calculate stake size based on:
        - 2% of current balance
        - ATR-based stop distance

        Returns stake amount in account currency.
        """
        if not balance or balance <= 0:
            return None
        if not atr or atr <= 0:
            return None

        # Risk amount in currency
        risk_amount = balance * RISK_PER_TRADE_PCT

        # Stake = risk amount (Deriv digital options stake = max loss)
        stake = round(risk_amount, 2)

        # Minimum stake enforcement
        if stake < 0.35:
            stake = 0.35

        return stake

    def calculate_sl_tp(self, entry_price: float, atr: float,
                        direction: str):
        """
        Calculate stop-loss and take-profit levels.
        SL = ATR x 1.5
        TP = ATR x 3.0 (minimum 1:2 RR)
        """
        from config import ATR_STOP_MULTIPLIER, ATR_TP_MULTIPLIER

        if not atr or atr <= 0:
            return None, None

        sl_distance = atr * ATR_STOP_MULTIPLIER
        tp_distance = atr * ATR_TP_MULTIPLIER

        if direction == "BUY":
            stop_loss   = round(entry_price - sl_distance, 5)
            take_profit = round(entry_price + tp_distance, 5)
        elif direction == "SELL":
            stop_loss   = round(entry_price + sl_distance, 5)
            take_profit = round(entry_price - tp_distance, 5)
        else:
            return None, None

        return stop_loss, take_profit

    def get_risk_reward(self, entry: float, sl: float, tp: float):
        """Calculate actual risk:reward ratio"""
        if not all([entry, sl, tp]):
            return None
        risk   = abs(entry - sl)
        reward = abs(entry - tp)
        if risk == 0:
            return None
        return round(reward / risk, 2)