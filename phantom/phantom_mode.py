import random
from datetime import datetime, timezone
from config import MIN_DAILY_TRADES, MAX_DAILY_TRADES

class PhantomMode:

    ACTIVE   = "ACTIVE"    # Watching and trading
    SHUTDOWN = "SHUTDOWN"  # Daily cap hit — done for today

    def __init__(self):
        self.state          = self.ACTIVE
        self.trades_today   = 0
        self.daily_trade_cap = 0
        self.shutdown_reason = None
        self.day_seed       = None

        # Generate today's settings immediately
        self._daily_reset()

    def _daily_reset(self):
        """
        Called at startup and every midnight.
        Rolls a new random trade cap for the day.
        """
        self.day_seed        = random.randint(10000000, 99999999)
        self.daily_trade_cap = random.randint(
            MIN_DAILY_TRADES, MAX_DAILY_TRADES
        )
        self.trades_today    = 0
        self.state           = self.ACTIVE
        self.shutdown_reason = None

        print(f"\n[PHANTOM] 🎲 New day initialized")
        print(f"[PHANTOM] Seed         : {self.day_seed}")
        print(f"[PHANTOM] Trade cap    : {self.daily_trade_cap} trades")
        print(f"[PHANTOM] State        : {self.state}")
        print(f"[PHANTOM] Bot is LIVE and watching all pairs...\n")

    def can_trade(self):
        """Returns True as long as daily cap not reached"""
        return (
            self.state == self.ACTIVE and
            self.trades_today < self.daily_trade_cap
        )

    def register_trade(self):
        """Call every time a trade is opened"""
        self.trades_today += 1
        remaining = self.daily_trade_cap - self.trades_today

        print(f"[PHANTOM] Trade #{self.trades_today} registered | "
              f"{remaining} remaining today")

        if self.trades_today >= self.daily_trade_cap:
            self.state           = self.SHUTDOWN
            self.shutdown_reason = "Daily trade cap reached"
            print(f"\n[PHANTOM] 🛑 SHUTDOWN — "
                  f"Daily cap of {self.daily_trade_cap} trades reached.")
            print(f"[PHANTOM] SOVEREIGN is done for today. "
                  f"Resetting at midnight.")

    def emergency_shutdown(self, reason: str):
        """Called by circuit breaker when loss limit is hit"""
        self.state           = self.SHUTDOWN
        self.shutdown_reason = reason
        print(f"\n[PHANTOM] 🚨 EMERGENCY SHUTDOWN")
        print(f"[PHANTOM] Reason: {reason}")

    def check_midnight_reset(self):
        """
        Call this every tick.
        Automatically resets at midnight UTC.
        """
        now = datetime.now(timezone.utc)
        if (now.hour == 0 and
                now.minute == 0 and
                now.second < 5 and
                self.state == self.SHUTDOWN):
            print(f"\n[PHANTOM] 🌅 Midnight — resetting for new day")
            self._daily_reset()

    def get_status(self):
        """Return current phantom status"""
        return {
            "state":          self.state,
            "seed":           self.day_seed,
            "trades_today":   self.trades_today,
            "trade_cap":      self.daily_trade_cap,
            "remaining":      self.daily_trade_cap - self.trades_today,
            "can_trade":      self.can_trade(),
            "shutdown_reason": self.shutdown_reason
        }