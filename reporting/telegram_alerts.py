import httpx
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_IDS

class TelegramAlerts:
    def __init__(self):
        self.token    = TELEGRAM_BOT_TOKEN
        self.chat_ids = [c for c in TELEGRAM_CHAT_IDS if c]
        self.base_url = f"https://api.telegram.org/bot{self.token}"

    async def send(self, message: str):
        """Send message to all recipients"""
        if not self.token or not self.chat_ids:
            print("[TELEGRAM] Not configured — skipping alert")
            return

        for chat_id in self.chat_ids:
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        f"{self.base_url}/sendMessage",
                        json={
                            "chat_id":    chat_id,
                            "text":       message,
                            "parse_mode": "HTML"
                        },
                        timeout=10
                    )
                    if response.status_code == 200:
                        print(f"[TELEGRAM] ✅ Sent to {chat_id}")
                    else:
                        print(f"[TELEGRAM] ❌ Failed {chat_id}: "
                              f"{response.text}")
            except Exception as e:
                print(f"[TELEGRAM] Error: {e}")

    async def trade_opened(self, trade: dict, stake: float,
                           sl: float, tp: float, rr: float):
        """Alert when trade opens"""
        direction_emoji = "📈" if trade["direction"] == "BUY" else "📉"
        engine_emoji    = "🏄" if trade["engine"] == "DRIFT_RIDER" \
                          else "🚨"
        msg = (
            f"{engine_emoji} <b>SOVEREIGN — TRADE OPENED</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"📊 Pair      : <b>{trade['pair']}</b>\n"
            f"{direction_emoji} Direction : <b>{trade['direction']}</b>\n"
            f"🎯 Engine    : {trade['engine']}\n"
            f"💰 Stake     : <b>${stake:.2f}</b>\n"
            f"🛑 Stop Loss : {sl}\n"
            f"✅ Take Profit: {tp}\n"
            f"⚖️  R:R       : 1:{rr}\n"
            f"🔑 Contract  : {trade['contract_id']}\n"
            f"━━━━━━━━━━━━━━━━━━━━"
        )
        await self.send(msg)

    async def trade_closed(self, trade: dict, new_balance: float,
                           daily_pnl: float, win_rate: float):
        """Alert when trade closes"""
        result_emoji = "✅ WIN" if trade["result"] == "WIN" else "❌ LOSS"
        pnl_sign     = "+" if (trade["pnl"] or 0) > 0 else ""
        msg = (
            f"{result_emoji}\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"📊 Pair     : <b>{trade['pair']}</b>\n"
            f"🎯 Engine   : {trade['engine']}\n"
            f"💵 P&L      : <b>{pnl_sign}{trade['pnl']:.2f}</b>\n"
            f"💼 Balance  : ${new_balance:.2f}\n"
            f"📈 Daily P&L: {'+' if daily_pnl > 0 else ''}"
            f"{daily_pnl:.2f}\n"
            f"🏆 Win Rate : {win_rate}%\n"
            f"━━━━━━━━━━━━━━━━━━━━"
        )
        await self.send(msg)

    async def spike_alert(self, pair: str, direction: str,
                          move_size: float, ticks_since: int):
        """Alert when spike detected"""
        emoji = "💥" if direction == "DOWN" else "🚀"
        msg = (
            f"{emoji} <b>SPIKE DETECTED</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"📊 Pair      : <b>{pair}</b>\n"
            f"📉 Direction : {direction}\n"
            f"📏 Move Size : {move_size:.3f} pts\n"
            f"🕐 After     : {ticks_since} ticks\n"
            f"━━━━━━━━━━━━━━━━━━━━"
        )
        await self.send(msg)

    async def daily_summary(self, phantom_status: dict,
                            circuit_status: dict, win_rate: float):
        """Send daily summary report"""
        pnl     = circuit_status.get("daily_pnl", 0)
        balance = circuit_status.get("current_balance", 0)
        trades  = phantom_status.get("trades_today", 0)
        cap     = phantom_status.get("trade_cap", 0)
        performance = "🟢 PROFITABLE" if pnl > 0 else "🔴 LOSS DAY"
        msg = (
            f"📋 <b>SOVEREIGN — DAILY SUMMARY</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"{performance}\n"
            f"💰 P&L      : {'+' if pnl > 0 else ''}{pnl:.2f}\n"
            f"💼 Balance  : ${balance:.2f}\n"
            f"📊 Trades   : {trades}/{cap}\n"
            f"🏆 Win Rate : {win_rate}%\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"🤖 SOVEREIGN signing off for today."
        )
        await self.send(msg)

    async def system_alert(self, message: str):
        """Send system/emergency alert"""
        msg = (
            f"⚠️ <b>SOVEREIGN SYSTEM ALERT</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"{message}\n"
            f"━━━━━━━━━━━━━━━━━━━━"
        )
        await self.send(msg)

    async def startup_message(self, balance: float,
                              trade_cap: int, seed: int):
        """Send message when bot starts"""
        msg = (
            f"🏛️ <b>SOVEREIGN IS LIVE</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"💼 Balance   : ${balance:.2f}\n"
            f"🎯 Trade Cap : {trade_cap} trades today\n"
            f"🎲 Day Seed  : {seed}\n"
            f"📊 Pairs     : CRASH500 | BOOM500\n"
            f"             CRASH1000 | BOOM1000\n"
            f"🔥 Engines   : Spike Catcher + Drift Rider\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"👁️ Watching all pairs for signals..."
        )
        await self.send(msg)