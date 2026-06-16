import asyncio
from datetime import datetime, timezone, timedelta

from core.connection import DerivConnection
from core.tick_stream import TickStream
from core.candle_builder import CandleBuilder
from core.spike_logger import SpikeLogger
from signals.velocity import VelocityCalculator
from signals.candle_shrink import CandleShrinkDetector
from signals.rsi import RSICalculator
from signals.ema import EMACalculator, ATRCalculator
from signals.tick_zone import TickZoneDetector
from engines.spike_catcher import SpikeCatcher
from engines.drift_rider import DriftRider
from phantom.phantom_mode import PhantomMode
from risk.sizer import PositionSizer
from risk.circuit_breaker import CircuitBreaker
from broker.trade_executor import TradeExecutor
from reporting.telegram_alerts import TelegramAlerts
from reporting.supabase_logger import SupabaseLogger
from keep_alive import keep_alive
from config import PAIRS

# ── Global components ──────────────────────────────────────────────────────────
candle_builder  = CandleBuilder(candle_duration_seconds=60)
spike_logger    = SpikeLogger()
velocity        = VelocityCalculator()
shrink          = CandleShrinkDetector()
rsi             = RSICalculator(period=14)
ema             = EMACalculator()
atr_calc        = ATRCalculator()
tick_zone       = TickZoneDetector()
phantom         = PhantomMode()
sizer           = PositionSizer()
circuit_breaker = CircuitBreaker()
telegram        = TelegramAlerts()
db              = SupabaseLogger()

# Initialized after connection
executor        = None
spike_catcher   = None
drift_rider     = None
account_balance = 10000.0
opening_balance = 10000.0

# WAT = UTC+1
WAT = timezone(timedelta(hours=1))


# ── Midnight handler ───────────────────────────────────────────────────────────
async def handle_midnight_reset():
    """Send daily summary, log to Supabase, then reset phantom."""
    global account_balance

    print("[SOVEREIGN] 🌙 Midnight WAT — running daily wrap-up...")

    ph_status   = phantom.get_status()
    cb_status   = circuit_breaker.get_status()
    wr          = executor.get_win_rate() if executor else 0
    history     = executor.get_trade_history() if executor else []
    closing_bal = account_balance

    await telegram.daily_summary(ph_status, cb_status, wr)

    db.log_daily_summary(
        opening_balance,
        closing_bal,
        history,
        ph_status
    )

    phantom.check_midnight_reset()

    print("[SOVEREIGN] ✅ Daily wrap-up complete. New day started.")


# ── Tick handler ───────────────────────────────────────────────────────────────
async def on_tick(pair, tick_data):
    global account_balance

    price = tick_data["price"]

    # Feed all components
    candle_builder.process_tick(pair, tick_data)
    velocity.process_tick(pair, price)
    spike = spike_logger.process_tick(pair, tick_data)

    # Midnight reset check
    if phantom.check_midnight_reset():
        await handle_midnight_reset()

    # Spike detected — notify drift rider and log
    if spike:
        drift_rider.reset_after_spike(pair)

        db.log_spike({
            "pair":             pair,
            "direction":        spike.get("direction"),
            "move_size":        spike.get("move_size"),
            "price_before":     spike.get("price_before"),
            "price_after":      spike.get("price_after"),
            "ticks_since_last": spike.get("ticks_since_last", 0)
        })

        await telegram.spike_alert(
            pair,
            spike.get("direction"),
            spike.get("move_size", 0),
            spike.get("ticks_since_last", 0)
        )

    # If pair already has open trade — check if it closed
    if executor.has_open_trade(pair):
        closed_trade = await executor.check_trade(pair)

        if closed_trade:
            account_balance += closed_trade.get("pnl", 0)
            circuit_breaker.update_balance(account_balance)
            db.log_trade_closed(closed_trade)
            await telegram.trade_closed(
                closed_trade,
                account_balance,
                executor.get_daily_pnl(),
                executor.get_win_rate()
            )
        return

    # ── Gate checks ───────────────────────────────────────────────────────────
    if not phantom.can_trade():
        return
    if not circuit_breaker.is_safe():
        await telegram.system_alert(
            "⛔ Circuit breaker triggered — daily loss limit reached.\n"
            "SOVEREIGN has shut down trading for today."
        )
        return

    # ── Prepare stake and ATR ─────────────────────────────────────────────────
    highs  = candle_builder.get_highs(pair)
    lows   = candle_builder.get_lows(pair)
    closes = candle_builder.get_closes(pair)
    atr    = atr_calc.calculate(highs, lows, closes) or 0.5
    stake  = sizer.calculate(account_balance, atr) or 1.0

    from config import ATR_STOP_MULTIPLIER, ATR_TP_MULTIPLIER
    rr = round(ATR_TP_MULTIPLIER / ATR_STOP_MULTIPLIER, 1)

    # ── ENGINE 1: Drift Rider (evaluated on EVERY tick after a spike) ─────────
    dr_eval = drift_rider.evaluate(pair)
    if dr_eval["should_enter"]:
        print(f"\n🏄 DRIFT RIDER ENTRY [{pair}]")
        trade = await executor.open_trade(
            pair,
            dr_eval["direction"],
            stake,
            "DRIFT_RIDER"
        )
        if trade:
            phantom.register_trade()
            drift_rider.confirm_entry(pair)

            entry     = trade.get("buy_price", price)
            direction = dr_eval["direction"]
            if direction == "BUY":
                sl = round(entry - (atr * ATR_STOP_MULTIPLIER), 5)
                tp = round(entry + (atr * ATR_TP_MULTIPLIER), 5)
            else:
                sl = round(entry + (atr * ATR_STOP_MULTIPLIER), 5)
                tp = round(entry - (atr * ATR_TP_MULTIPLIER), 5)

            db.log_trade_opened(trade, stake, atr, {
                "score":             0,
                "signals":           {},
                "rsi_value":         dr_eval.get("rsi"),
                "ema_trend":         dr_eval.get("ema200"),
                "ticks_since_spike": spike_logger.get_ticks_since_spike(pair)
            })
            await telegram.trade_opened(trade, stake, sl, tp, rr)
        return

    # ── ENGINE 2: Spike Catcher ───────────────────────────────────────────────
    sc_eval = spike_catcher.evaluate(pair)
    if sc_eval["should_enter"]:
        print(f"\n🚨 SPIKE CATCHER ENTRY [{pair}]")
        trade = await executor.open_trade(
            pair,
            sc_eval["direction"],
            stake,
            "SPIKE_CATCHER"
        )
        if trade:
            phantom.register_trade()
            spike_catcher.confirm_entry(
                pair,
                spike_logger.get_ticks_since_spike(pair)
            )

            entry     = trade.get("buy_price", price)
            direction = sc_eval["direction"]
            if direction == "BUY":
                sl = round(entry - (atr * ATR_STOP_MULTIPLIER), 5)
                tp = round(entry + (atr * ATR_TP_MULTIPLIER), 5)
            else:
                sl = round(entry + (atr * ATR_STOP_MULTIPLIER), 5)
                tp = round(entry - (atr * ATR_TP_MULTIPLIER), 5)

            db.log_trade_opened(trade, stake, atr, sc_eval)
            await telegram.trade_opened(trade, stake, sl, tp, rr)


# ── Status monitor ─────────────────────────────────────────────────────────────
async def status_monitor():
    """Print live status to console every 30 seconds."""
    await asyncio.sleep(30)
    while True:
        ph  = phantom.get_status()
        cb  = circuit_breaker.get_status()
        wr  = executor.get_win_rate() if executor else 0
        pnl = executor.get_daily_pnl() if executor else 0

        now_wat = datetime.now(WAT).strftime("%H:%M:%S")

        print(f"\n{'='*55}")
        print(f"  SOVEREIGN LIVE STATUS  [{now_wat} WAT]")
        print(f"{'='*55}")
        print(f"  Phantom : {ph['state']} | "
              f"Trades: {ph['trades_today']}/{ph['trade_cap']}")
        print(f"  P&L     : ${pnl:.2f} | Win Rate: {wr}%")
        print(f"  Circuit : Safe={cb.get('is_safe', True)} | "
              f"Loss: {cb.get('daily_pnl_pct', 0):.2f}%")

        for pair in PAIRS:
            ticks    = spike_logger.get_ticks_since_spike(pair)
            sc       = spike_catcher.evaluate(pair)
            has_open = executor.has_open_trade(pair) if executor else False
            print(f"  {pair:<12} | Ticks: {ticks:<4} | "
                  f"SC: {sc['score']}/5 | "
                  f"Open: {'YES' if has_open else 'no'}")

        print(f"{'='*55}")
        await asyncio.sleep(30)


# ── Main ───────────────────────────────────────────────────────────────────────
async def main():
    global executor, account_balance, opening_balance
    global spike_catcher, drift_rider

    print("\n[SOVEREIGN] 🏛️  Initializing...")
    keep_alive()  # ← Flask keepalive for Render

    # 1. Test Supabase connection
    print("[SOVEREIGN] Testing Supabase connection...")
    if not db.enabled:
        print("[SOVEREIGN] ⚠️  Supabase disabled — check .env keys")
    else:
        print("[SOVEREIGN] ✅ Supabase ready")

    # 2. Connect to Deriv
    conn = DerivConnection()
    success = await conn.connect()
    if not success:
        await telegram.system_alert("❌ SOVEREIGN failed to connect to Deriv.")
        print("[SOVEREIGN] Cannot connect to Deriv. Exiting.")
        return

    # 3. Initialize executor
    executor = TradeExecutor(conn)

    # 4. Fetch live balance
    await conn.send({"balance": 1, "account": "current"})
    for _ in range(5):
        resp = await conn.receive()
        if resp and "balance" in resp:
            account_balance = float(resp["balance"]["balance"])
            opening_balance = account_balance
            print(f"[SOVEREIGN] 💼 Live balance: ${account_balance:.2f}")
            break

    circuit_breaker.set_opening_balance(account_balance)

    # 5. Initialize engines
    spike_catcher = SpikeCatcher(
        candle_builder, spike_logger,
        velocity, shrink, rsi, ema, tick_zone
    )
    drift_rider = DriftRider(
        candle_builder, spike_logger,
        ema, rsi, velocity
    )

    # 6. Subscribe to tick streams
    stream = TickStream(conn)
    await stream.subscribe_all()

    # 7. Send Telegram startup message
    ph_status = phantom.get_status()
    await telegram.startup_message(
        account_balance,
        ph_status["trade_cap"],
        ph_status.get("seed", 0)
    )

    print("\n[SOVEREIGN] 🚀 FULLY ARMED AND OPERATIONAL")
    print("[SOVEREIGN] Running indefinitely. Press Ctrl+C to stop.\n")

    # 8. Run forever
    try:
        await asyncio.gather(
            stream.listen(on_tick_callback=on_tick),
            conn.keep_alive(),
            status_monitor()
        )
    except KeyboardInterrupt:
        print("\n[SOVEREIGN] ⛔ Manual stop detected.")
    except Exception as e:
        print(f"\n[SOVEREIGN] Stopped unexpectedly: {e}")
        await telegram.system_alert(f"⛔ SOVEREIGN stopped unexpectedly:\n{e}")

    # 9. Final wrap-up on exit
    ph_status = phantom.get_status()
    cb_status = circuit_breaker.get_status()
    wr        = executor.get_win_rate()
    history   = executor.get_trade_history()
    pnl       = executor.get_daily_pnl()

    print(f"\n{'='*55}")
    print(f"  SOVEREIGN FINAL REPORT")
    print(f"{'='*55}")
    print(f"  Trades taken : {ph_status['trades_today']}")
    print(f"  Win rate     : {wr}%")
    print(f"  Total P&L    : ${pnl:.2f}")
    print(f"  Trade history: {len(history)} closed trades")
    print(f"{'='*55}")

    db.log_daily_summary(
        opening_balance,
        account_balance,
        history,
        ph_status
    )
    await telegram.daily_summary(ph_status, cb_status, wr)

    await stream.unsubscribe_all()
    await conn.disconnect()
    print("[SOVEREIGN] 🏛️  Shutdown complete.")


if __name__ == "__main__":
    asyncio.run(main())