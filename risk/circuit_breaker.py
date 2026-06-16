from config import DAILY_LOSS_LIMIT_PCT

class CircuitBreaker:
    def __init__(self):
        self.opening_balance = None
        self.current_balance = None
        self.daily_pnl       = 0.0
        self.triggered       = False
        self.trigger_reason  = None

    def set_opening_balance(self, balance: float):
        """Call once at start of day with account balance"""
        self.opening_balance = balance
        self.current_balance = balance
        self.daily_pnl       = 0.0
        self.triggered       = False
        print(f"[CIRCUIT BREAKER] Opening balance: {balance}")
        print(f"[CIRCUIT BREAKER] Daily loss limit: "
              f"{balance * DAILY_LOSS_LIMIT_PCT:.2f} "
              f"({DAILY_LOSS_LIMIT_PCT * 100}%)")

    def update_balance(self, new_balance: float):
        """
        Call after every trade closes.
        Checks if daily loss limit has been hit.
        Returns True if circuit breaker triggered.
        """
        if self.opening_balance is None:
            return False

        self.current_balance = new_balance
        self.daily_pnl = new_balance - self.opening_balance

        loss_pct = self.daily_pnl / self.opening_balance

        if loss_pct <= -DAILY_LOSS_LIMIT_PCT:
            self.triggered     = True
            self.trigger_reason = (
                f"Daily loss limit hit: "
                f"{loss_pct * 100:.2f}% loss "
                f"(limit: {DAILY_LOSS_LIMIT_PCT * 100}%)"
            )
            print(f"\n[CIRCUIT BREAKER] 🚨 TRIGGERED!")
            print(f"[CIRCUIT BREAKER] {self.trigger_reason}")
            return True

        return False

    def is_safe(self):
        """Returns True if safe to trade"""
        return not self.triggered

    def get_status(self):
        """Return circuit breaker status"""
        if self.opening_balance is None:
            return {"status": "not initialized"}

        loss_pct = (self.daily_pnl / self.opening_balance) * 100

        return {
            "opening_balance": self.opening_balance,
            "current_balance": self.current_balance,
            "daily_pnl":       round(self.daily_pnl, 2),
            "daily_pnl_pct":   round(loss_pct, 2),
            "triggered":       self.triggered,
            "is_safe":         self.is_safe(),
            "trigger_reason":  self.trigger_reason
        }

    def daily_reset(self, new_balance: float):
        """Reset at midnight with new opening balance"""
        self.set_opening_balance(new_balance)
        print("[CIRCUIT BREAKER] Daily reset complete.")