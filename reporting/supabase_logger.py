import httpx
from config import SUPABASE_URL, SUPABASE_KEY

class SupabaseLogger:
    def __init__(self):
        if SUPABASE_URL and SUPABASE_KEY:
            self.url     = f"{SUPABASE_URL}/rest/v1"
            self.headers = {
                "apikey":        SUPABASE_KEY,
                "Authorization": f"Bearer {SUPABASE_KEY}",
                "Content-Type":  "application/json",
                "Prefer":        "return=minimal"
            }
            self.enabled = True
            print("[SUPABASE] ✅ Connected successfully")
        else:
            self.enabled = False
            print("[SUPABASE] ⚠️  Not configured — logging disabled")

    def _insert(self, table: str, data: dict):
        """POST a row into a table"""
        try:
            r = httpx.post(
                f"{self.url}/{table}",
                headers=self.headers,
                json=data,
                timeout=10
            )
            if r.status_code in (200, 201):
                return True
            else:
                print(f"[SUPABASE] Insert error {r.status_code}: {r.text}")
                return False
        except Exception as e:
            print(f"[SUPABASE] Insert exception: {e}")
            return False

    def _update(self, table: str, match_col: str,
                match_val: str, data: dict):
        """PATCH a row by matching a column value"""
        try:
            headers = {**self.headers, "Prefer": "return=minimal"}
            r = httpx.patch(
                f"{self.url}/{table}?{match_col}=eq.{match_val}",
                headers=headers,
                json=data,
                timeout=10
            )
            if r.status_code in (200, 204):
                return True
            else:
                print(f"[SUPABASE] Update error {r.status_code}: {r.text}")
                return False
        except Exception as e:
            print(f"[SUPABASE] Update exception: {e}")
            return False

    def _select(self, table: str, filters: dict = None):
        """GET rows from a table with optional filters"""
        try:
            params = {}
            if filters:
                for k, v in filters.items():
                    params[k] = f"eq.{v}"
            r = httpx.get(
                f"{self.url}/{table}",
                headers={**self.headers, "Prefer": ""},
                params=params,
                timeout=10
            )
            if r.status_code == 200:
                return r.json()
            else:
                print(f"[SUPABASE] Select error {r.status_code}: {r.text}")
                return []
        except Exception as e:
            print(f"[SUPABASE] Select exception: {e}")
            return []

    # ── Public methods (same interface as before) ──────────────────────────────

    def log_trade_opened(self, trade: dict, stake: float,
                         atr: float, sc_eval: dict):
        """Log trade when it opens"""
        if not self.enabled:
            return

        signals = sc_eval.get("signals", {})
        data = {
            "pair":              trade["pair"],
            "engine":            trade["engine"],
            "direction":         trade["direction"],
            "contract_id":       str(trade["contract_id"]),
            "stake":             stake,
            "buy_price":         trade.get("buy_price"),
            "atr_value":         atr,
            "sc_score":          sc_eval.get("score", 0),
            "s1_velocity":       signals.get("S1_velocity", False),
            "s2_shrinkage":      signals.get("S2_shrinkage", False),
            "s3_rsi":            signals.get("S3_rsi", False),
            "s4_ema":            signals.get("S4_ema", False),
            "s5_tick_zone":      signals.get("S5_tick_zone", False),
            "rsi_value":         sc_eval.get("rsi_value"),
            "ema_trend":         sc_eval.get("ema_trend"),
            "ticks_since_spike": sc_eval.get("ticks_since_spike", 0),
            "status":            "OPEN"
        }

        if self._insert("sovereign_trades", data):
            print(f"[SUPABASE] ✅ Trade opened logged: "
                  f"{trade['pair']} {trade['direction']}")

    def log_trade_closed(self, trade: dict):
        """Update trade record when it closes"""
        if not self.enabled:
            return

        contract_id = str(trade.get("contract_id"))
        data = {
            "sell_price": trade.get("sell_price"),
            "pnl":        trade.get("pnl"),
            "result":     trade.get("result"),
            "status":     "CLOSED"
        }

        if self._update("sovereign_trades", "contract_id", contract_id, data):
            print(f"[SUPABASE] ✅ Trade closed logged: "
                  f"{trade['pair']} {trade['result']} "
                  f"P&L: {trade.get('pnl')}")

    def log_spike(self, spike: dict):
        """Log every spike detected"""
        if not self.enabled:
            return

        data = {
            "pair":             spike["pair"],
            "direction":        spike["direction"],
            "move_size":        spike["move_size"],
            "price_before":     spike["price_before"],
            "price_after":      spike["price_after"],
            "ticks_since_last": spike["ticks_since_last"]
        }
        self._insert("sovereign_spikes", data)

    def log_daily_summary(self, opening_balance: float,
                          closing_balance: float,
                          trades: list, phantom_status: dict):
        """Log end of day summary"""
        if not self.enabled:
            return

        wins   = sum(1 for t in trades if t.get("result") == "WIN")
        losses = sum(1 for t in trades if t.get("result") == "LOSS")
        total  = len(trades)
        wr     = round(wins / total * 100, 1) if total > 0 else 0
        pnl    = closing_balance - opening_balance

        data = {
            "opening_balance": opening_balance,
            "closing_balance": closing_balance,
            "daily_pnl":       round(pnl, 2),
            "total_trades":    total,
            "wins":            wins,
            "losses":          losses,
            "win_rate":        wr,
            "trade_cap":       phantom_status.get("trade_cap", 0),
            "day_seed":        phantom_status.get("seed", 0)
        }

        if self._insert("sovereign_daily", data):
            print(f"[SUPABASE] ✅ Daily summary logged: "
                  f"P&L={pnl:.2f} | WR={wr}%")

    def get_today_trades(self):
        """Fetch today's closed trades"""
        if not self.enabled:
            return []
        return self._select("sovereign_trades", {"status": "CLOSED"})

    def get_win_rate_all_time(self):
        """Calculate all time win rate from database"""
        if not self.enabled:
            return 0.0

        trades = self._select("sovereign_trades", {"status": "CLOSED"})
        if not trades:
            return 0.0

        wins = sum(1 for t in trades if t.get("result") == "WIN")
        return round(wins / len(trades) * 100, 1)