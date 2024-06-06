import asyncio

from core.logging import *
import websockets


class Server:
    def __init__(self, port: str):
        self.port = int(port)

    async def deploy(self):
        async def handler(websocket: websockets.WebSocketServerProtocol, _):
            await websocket.send("Hello, Client!")

        async with websockets.serve(handler, "127.0.0.1", self.port):
            info(f"WebSocket server started on 127.0.0.1:{self.port}")
            info(f"<hint> use it for pwnat")
            await asyncio.Future()


__all__ = [
    'Server',
]