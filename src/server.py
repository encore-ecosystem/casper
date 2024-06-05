import json
import pprint
import re
from tqdm import tqdm
from src.utils import pair_tuple_to_dict
import websockets
import asyncio


class VCSWS_Server:
    def __init__(self, server_address: str, server_port: str):
        self.address     = server_address
        self.port        = int(server_port)
        self.connections = set()

    @staticmethod
    async def keep_ws_alive(websocket):
        while True:
            if websocket.closed:
                print(f"Websocket on {websocket.remote_address} closed.")
                break
            else:
                await websocket.keepalive_ping()

    async def run(self):
        async def handler(websocket: websockets.WebSocketServerProtocol, path):

            command = await websocket.recv()

            if   re.fullmatch(r"subscribe", command):
                address, port = websocket.remote_address
                print(f'New subscribe request: {address}:{port}')
                self.connections.add((f"{address}:{port}", websocket))
                await self.keep_ws_alive(websocket)

            elif re.fullmatch(r"sync", command):
                print('sync attempt')

                # get active subs
                print('active subscribers: ')
                available = set()
                for (full_address, ws) in self.connections:
                    if not ws.closed:
                        available.add((full_address, ws))
                self.connections = available
                pprint.pp(self.connections)

                # receive data from sync operator
                sync_operator_data = await websocket.recv()

                # translate it to active subs
                for (_, ws) in tqdm(self.connections):
                    await ws.send(sync_operator_data)

                # get download request
                to_download = {}
                for (full_address, ws) in tqdm(self.connections):
                    download_request = json.loads(await ws.recv())
                    for hash_ in download_request:
                        if hash_ in sync_operator_data:
                            to_download[hash_] = to_download.get(hash_, []) + [full_address]
                    # print(f"{full_address}: {download_request}")

                # send request to files
                address_book = pair_tuple_to_dict(self.connections)
                await websocket.send(json.dumps(list(to_download.keys())))
                for file_hash in tqdm(to_download):
                    data = await websocket.recv()
                    for full_address in to_download[file_hash]:
                        await address_book[full_address].send(data)

                # close connections
                for (ip, ws) in self.connections:
                    await ws.close()
                self.connections.clear()

        async with websockets.serve(handler, self.address, self.port):
            print("Server is running")
            await asyncio.Future()


__all__ = ["VCSWS_Server"]
