import websockets
from core.logging import *


class Client:
    def __init__(self, server_ip: str, server_port: str):
        self.server_ip   = server_ip
        self.server_port = server_port

    async def connect(self):
        info(f"Client started on ws://{self.server_ip}:{self.server_port}")
        async with websockets.connect(f"ws://{self.server_ip}:{self.server_port}") as websocket:
            answer = await websocket.recv()
            print(f"SERVER: {answer}")


__all__ = [
    'Client',
]