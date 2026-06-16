import asyncio
import json
import websockets
from config import DERIV_WS_URL, DERIV_API_TOKEN

class DerivConnection:
    def __init__(self):
        self.websocket = None
        self.connected = False
        self.reconnect_attempts = 0
        self.max_reconnects = 999
        self.reconnect_delay = 5

    async def connect(self):
        """Establish WebSocket connection to Deriv API"""
        while self.reconnect_attempts < self.max_reconnects:
            try:
                print(f"[SOVEREIGN] Connecting to Deriv API...")
                self.websocket = await websockets.connect(
                    DERIV_WS_URL,
                    ping_interval=None,
                    ping_timeout=None
                )
                self.connected = True
                self.reconnect_attempts = 0
                print(f"[SOVEREIGN] Connected successfully.")
                await self.authorize()
                return True

            except Exception as e:
                self.connected = False
                self.reconnect_attempts += 1
                print(f"[SOVEREIGN] Connection failed: {e}")
                print(f"[SOVEREIGN] Retrying in {self.reconnect_delay}s... "
                      f"(attempt {self.reconnect_attempts})")
                await asyncio.sleep(self.reconnect_delay)

        return False

    async def authorize(self):
        """Authenticate with Deriv API token"""
        await self.send({"authorize": DERIV_API_TOKEN})
        response = await self.receive()

        if response and "authorize" in response:
            account = response["authorize"]
            print(f"[SOVEREIGN] Authorized. Account: "
                  f"{account.get('email', 'N/A')}")
            print(f"[SOVEREIGN] Balance: "
                  f"{account.get('balance', 'N/A')} "
                  f"{account.get('currency', '')}")
            return True
        elif response and "error" in response:
            print(f"[SOVEREIGN] Auth failed: "
                  f"{response['error']['message']}")
            return False

    async def send(self, data: dict):
        """Send message to Deriv API"""
        if self.websocket and self.connected:
            try:
                await self.websocket.send(json.dumps(data))
            except Exception as e:
                self.connected = False
                print(f"[SOVEREIGN] Send error: {e}")

    async def receive(self):
        """Receive one message from Deriv API"""
        if self.websocket and self.connected:
            try:
                message = await self.websocket.recv()
                return json.loads(message)
            except Exception as e:
                self.connected = False
                print(f"[SOVEREIGN] Receive error: {e}")
                return None
        return None

    async def keep_alive(self):
        """
        Send Deriv-level ping every 25 seconds.
        Keeps connection alive without relying on websockets built-in ping.
        """
        while self.connected:
            try:
                await self.send({"ping": 1})
                await asyncio.sleep(25)
            except Exception:
                break

    async def disconnect(self):
        """Clean disconnect"""
        if self.websocket:
            self.connected = False
            try:
                await self.websocket.close()
            except Exception:
                pass
            print("[SOVEREIGN] Disconnected cleanly.")