import asyncio
from config import PAIR_SYMBOLS

class TradeExecutor:
    def __init__(self, connection):
        self.connection    = connection
        self.open_trades   = {}  # pair → trade details
        self.trade_history = []  # all closed trades

    def _get_contract_type(self, pair: str, direction: str):
        """
        Boom/Crash synthetic indices use RISE/FALL for tick contracts.
        RISE = price goes UP
        FALL = price goes DOWN
        """
        if direction == "BUY":
            return "RISE"
        elif direction == "SELL":
            return "FALL"
        return None

    async def open_trade(self, pair: str, direction: str,
                         stake: float, engine: str):
        """
        Open a trade on Deriv.
        Uses 5-tick duration (matches our 5-minute timeframe logic).
        Returns trade result dict or None if failed.
        """
        symbol        = PAIR_SYMBOLS[pair]
        contract_type = self._get_contract_type(pair, direction)

        if not contract_type:
            print(f"[EXECUTOR] Invalid direction: {direction}")
            return None

        # Build buy request
        request = {
            "buy": 1,
            "price": stake,
            "parameters": {
                "contract_type": contract_type,
                "symbol":        symbol,
                "duration":      5,
                "duration_unit": "t",  # ticks
                "basis":         "stake",
                "amount":        stake,
                "currency":      "USD"
            }
        }

        print(f"\n[EXECUTOR] Opening trade...")
        print(f"  Pair      : {pair}")
        print(f"  Direction : {direction} ({contract_type})")
        print(f"  Stake     : ${stake}")
        print(f"  Engine    : {engine}")

        await self.connection.send(request)

        # Wait for buy confirmation
        for _ in range(10):
            response = await self.connection.receive()

            if response is None:
                print("[EXECUTOR] No response from API")
                return None

            if "buy" in response:
                buy_data    = response["buy"]
                contract_id = buy_data.get("contract_id")
                buy_price   = buy_data.get("buy_price")
                longcode    = buy_data.get("longcode", "")

                trade = {
                    "contract_id":   contract_id,
                    "pair":          pair,
                    "direction":     direction,
                    "contract_type": contract_type,
                    "stake":         stake,
                    "buy_price":     buy_price,
                    "engine":        engine,
                    "status":        "OPEN",
                    "longcode":      longcode,
                    "pnl":           None,
                    "result":        None
                }

                self.open_trades[pair] = trade

                print(f"  ✅ Trade opened!")
                print(f"  Contract ID : {contract_id}")
                print(f"  Buy price   : {buy_price}")

                return trade

            elif "error" in response:
                error_msg = response["error"]["message"]
                print(f"  ❌ Trade failed: {error_msg}")
                return None

        print("[EXECUTOR] Timeout waiting for trade confirmation")
        return None

    async def check_trade(self, pair: str):
        """
        Check status of an open trade.
        Returns updated trade dict or None.
        """
        if pair not in self.open_trades:
            return None

        trade       = self.open_trades[pair]
        contract_id = trade["contract_id"]

        request = {
            "proposal_open_contract": 1,
            "contract_id": contract_id
        }

        await self.connection.send(request)

        for _ in range(5):
            response = await self.connection.receive()

            if response and "proposal_open_contract" in response:
                contract   = response["proposal_open_contract"]
                status     = contract.get("status")
                pnl        = contract.get("profit")
                sell_price = contract.get("sell_price")
                is_expired = contract.get("is_expired", False)
                is_sold    = contract.get("is_sold", False)

                trade["status"]     = status
                trade["pnl"]        = pnl
                trade["sell_price"] = sell_price

                if is_expired or is_sold or status == "sold":
                    trade["result"] = "WIN" if (pnl and pnl > 0) else "LOSS"
                    self.trade_history.append(dict(trade))
                    del self.open_trades[pair]

                    print(f"\n[EXECUTOR] Trade closed [{pair}]")
                    print(f"  Result : {trade['result']}")
                    print(f"  P&L    : {pnl}")

                return trade

        return None

    async def close_trade_early(self, pair: str):
        """
        Sell/close a contract before expiry.
        Used by exit logic when drift exhausts.
        """
        if pair not in self.open_trades:
            return None

        trade       = self.open_trades[pair]
        contract_id = trade["contract_id"]

        request = {
            "sell": contract_id,
            "price": 0  # sell at market price
        }

        await self.connection.send(request)

        for _ in range(5):
            response = await self.connection.receive()

            if response and "sell" in response:
                sell_data = response["sell"]
                sold_for  = sell_data.get("sold_for")
                pnl       = sold_for - trade["stake"] \
                            if sold_for else None

                trade["result"]     = "WIN" if (pnl and pnl > 0) else "LOSS"
                trade["pnl"]        = pnl
                trade["sell_price"] = sold_for
                trade["status"]     = "sold"

                self.trade_history.append(dict(trade))
                del self.open_trades[pair]

                print(f"\n[EXECUTOR] Trade closed early [{pair}]")
                print(f"  Sold for : {sold_for}")
                print(f"  P&L      : {pnl}")
                print(f"  Result   : {trade['result']}")

                return trade

            elif response and "error" in response:
                print(f"[EXECUTOR] Close error: "
                      f"{response['error']['message']}")
                return None

        return None

    def get_open_trade(self, pair: str):
        """Return open trade for a pair if exists"""
        return self.open_trades.get(pair)

    def has_open_trade(self, pair: str):
        """Check if pair has an open trade"""
        return pair in self.open_trades

    def get_trade_history(self):
        """Return all closed trades"""
        return self.trade_history

    def get_daily_pnl(self):
        """Calculate total P&L from closed trades today"""
        total = sum(
            t["pnl"] for t in self.trade_history
            if t["pnl"] is not None
        )
        return round(total, 2)

    def get_win_rate(self):
        """Calculate win rate from trade history"""
        if not self.trade_history:
            return 0.0
        wins = sum(
            1 for t in self.trade_history
            if t["result"] == "WIN"
        )
        return round(wins / len(self.trade_history) * 100, 1)