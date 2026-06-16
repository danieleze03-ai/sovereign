import asyncio
import json
from collections import deque
from config import PAIR_SYMBOLS, PAIRS

class TickStream:
    def __init__(self, connection):
        self.connection = connection

        # Rolling buffer — last 1000 ticks per pair
        self.tick_buffers = {pair: deque(maxlen=1000) for pair in PAIRS}

        # Latest price per pair
        self.latest_price = {pair: None for pair in PAIRS}

        # Tick counter since last spike per pair
        self.tick_counts = {pair: 0 for pair in PAIRS}

        # Last price per pair (to detect spikes)
        self.previous_price = {pair: None for pair in PAIRS}

        # Subscription IDs
        self.subscription_ids = {}

        # Running flag
        self.running = False

    async def subscribe_all(self):
        """Subscribe to tick feed for all 4 pairs"""
        for pair in PAIRS:
            symbol = PAIR_SYMBOLS[pair]
            request = {
                "ticks": symbol,
                "subscribe": 1
            }
            await self.connection.send(request)
            print(f"[TICK STREAM] Subscribed to {pair} ({symbol})")
            await asyncio.sleep(0.5)  # small delay between subscriptions

    async def unsubscribe_all(self):
        """Unsubscribe from all tick feeds"""
        for pair, sub_id in self.subscription_ids.items():
            request = {
                "forget": sub_id
            }
            await self.connection.send(request)
            print(f"[TICK STREAM] Unsubscribed from {pair}")

    def get_pair_from_symbol(self, symbol: str):
        """Reverse lookup — symbol to pair name"""
        for pair, sym in PAIR_SYMBOLS.items():
            if sym == symbol:
                return pair
        return None

    async def listen(self, on_tick_callback=None):
        """
        Main listening loop.
        Receives all incoming ticks and routes them to correct pair buffer.
        Calls on_tick_callback(pair, tick_data) for every tick received.
        """
        self.running = True
        print("[TICK STREAM] Listening for ticks on all pairs...")

        while self.running:
            try:
                message = await self.connection.receive()

                if message is None:
                    print("[TICK STREAM] No message received. Reconnecting...")
                    break

                # Handle tick data
                if "tick" in message:
                    tick = message["tick"]
                    symbol = tick.get("symbol")
                    price = float(tick.get("quote", 0))
                    timestamp = tick.get("epoch")
                    pair = self.get_pair_from_symbol(symbol)

                    if pair:
                        # Store tick in buffer
                        tick_data = {
                            "price": price,
                            "timestamp": timestamp,
                            "tick_number": self.tick_counts[pair]
                        }
                        self.tick_buffers[pair].append(tick_data)

                        # Update latest price
                        self.latest_price[pair] = price

                        # Increment tick counter
                        self.tick_counts[pair] += 1

                        # Store subscription ID for later unsubscribe
                        if "subscription" in message:
                            sub_id = message["subscription"].get("id")
                            if sub_id and pair not in self.subscription_ids:
                                self.subscription_ids[pair] = sub_id

                        # Fire callback if provided
                        if on_tick_callback:
                            await on_tick_callback(pair, tick_data)

                # Handle errors
                elif "error" in message:
                    print(f"[TICK STREAM] Error: {message['error']['message']}")

                # Handle ping response
                elif "ping" in message:
                    pass  # silent — ping is just keepalive

            except Exception as e:
                print(f"[TICK STREAM] Exception: {e}")
                self.running = False
                break

    def get_buffer(self, pair: str):
        """Return tick buffer for a pair"""
        return list(self.tick_buffers[pair])

    def get_latest_price(self, pair: str):
        """Return latest price for a pair"""
        return self.latest_price[pair]

    def get_tick_count(self, pair: str):
        """Return current tick count since last spike"""
        return self.tick_counts[pair]

    def reset_tick_count(self, pair: str):
        """Reset tick counter after a spike is detected"""
        self.tick_counts[pair] = 0

    def stop(self):
        """Stop the tick stream"""
        self.running = False
        print("[TICK STREAM] Stopped.")