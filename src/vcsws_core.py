import os
import re

import stun
import tqdm
import json
import pprint
import pickle
import tomllib
import hashlib
import asyncio
import datetime
import websockets

from pathlib import Path
from src.logger import Logger
from src.utils import *


class VCSWS:
    project_root: Path
    vcsws_path: Path
    manifest_path: Path
    project_name: str
    ignore_list: list
    branch: str = 'main'

    #
    # MAGIC
    #
    def __init__(self, logger: Logger, save_progress: bool = False):
        self.logger                             = logger
        self.save                               = save_progress
        self.initialized                        = False
        self.manifest                           = {}
        _, self.external_ip, self.external_port = stun.get_ip_info()

    def __str__(self) -> str:
        return f'[{self.get_project_name()}]'

    #
    # INTERFACE
    #
    def init(self, project_path):
        project_root = Path(project_path.strip(" '\"")).absolute()
        if not project_root.exists() or not project_root.is_dir():
            print('[Error] Project path invalid')
            return

        self.project_root  = project_root
        self.vcsws_path    = self.project_root / '.vcsws'
        self.manifest_path = self.vcsws_path / 'manifest.toml'
        self.project_name  = self.project_root.name

        self.load_manifest()
        self.load_ignore()

    def make_new_branch(self, branch_name: str):
        if not (self.vcsws_path / 'branches' / branch_name).exists():
            (self.vcsws_path / 'branches' / branch_name).mkdir()

    def relocate(self, branch_name: str):
        if branch_name in os.listdir(self.vcsws_path / 'branches'):
            self.branch = branch_name

    def status(self):
        hashes = self.logger(self.hash_it, Path())
        for h in hashes:
            print(*h, sep='   ')

    def commit(self, commit_name: str, commit_description: str):
        if len(commit_name) == 0:
            print('[Error]: Please, enter a non-empty commit name')
        else:
            with open(self.vcsws_path / 'branches' / self.branch / commit_name, 'w') as commit_file:
                commit_file.write(commit_description + '\n')

                for hash_, file_path in self.hash_it(self.vcsws_path.parent):
                    commit_file.write(f"{hash_} : {file_path}\n")

    def ignore(self, path: str):
        vcswsignore_path = (
            Path(self.vcsws_path / self.manifest.get('vcswsignore'))
            if 'vcswsignore' in self.manifest
            else Path(self.vcsws_path / '.vcswsignore')
        )
        if not vcswsignore_path.exists():
            safe_touch(vcswsignore_path)

        if path == '':
            self.load_ignore()
        else:
            abs_path = self.project_root / path
            if abs_path.exists():
                with open(vcswsignore_path, "a") as file:
                    file.write(f"{path}\n")
        self.load_ignore()

    async def push(self, address: str):
        async with websockets.connect(address) as ws:
            await ws.send("push")
            to_send = self.logger(self.hash_it, Path())
            data = {}
            for (hash_, path_) in to_send:
                data[hash_] =  path_

            await ws.send(json.dumps(data))

            to_download = json.loads(await ws.recv())
            for file_hash in tqdm.tqdm(to_download):
                with open(self.project_root / data[file_hash], 'rb') as binfile:
                    await ws.send(binfile.read())

            print("Completed")

    async def pull(self, address: str):
        async with websockets.connect(address) as ws:
            await ws.send("pull main")

    async def deploy(self):
        deploy_is_running = True

        async def handler(websocket: websockets.WebSocketServerProtocol, path):
            print(f"[{datetime.datetime.now()}] New connection from {websocket.remote_address}")
            command = await websocket.recv()
            nonlocal deploy_is_running
            if re.fullmatch(r"pull", command):
                print('pulling', command)

                #
                deploy_is_running = False

            elif re.fullmatch(r"push", command):
                # get datas
                server_data = {hash_: path_  for hash_, path_ in self.logger(self.hash_it, Path())}
                client_data = json.loads(await websocket.recv())
                files_to_pull = {}

                # compare hashes
                for hash_ in client_data:
                    if hash_ not in server_data:
                        if client_data[hash_] in server_data.values():
                            print(f'[U] Updated file in {client_data[hash_]}')

                            files_to_pull[hash_] = 'update'
                        else:
                            print(f'[+] New file in {client_data[hash_]}')
                            files_to_pull[hash_] = 'download'

                    else:
                        del server_data[hash_]

                for hash_ in server_data:
                    print(f'[D] Deleted file in {server_data[hash_]}')

                # download new files
                await websocket.send(json.dumps(files_to_pull))

                for hash_ in tqdm.tqdm(files_to_pull):
                    binfile = await websocket.recv()
                    safe_mkdir((self.project_root / client_data[hash_]).parent)
                    with open(self.project_root / client_data[hash_], 'wb') as f:
                        f.write(binfile)

                #
                deploy_is_running = False
            else:
                print('unexpected command', command)

        async with websockets.serve(handler, "0.0.0.0", self.external_port):

            print(f"[{datetime.datetime.now()}] Starting server...")
            print(f"[{datetime.datetime.now()}] Address: ws://{self.external_ip}:{self.external_port}")
            while deploy_is_running:
                await asyncio.sleep(5)
                print(f"[server status]: Ok")

    #
    # SUPPORT
    #
    def load_manifest(self):
        # Check existing of the project manifest
        if not self.vcsws_path.exists():
            self.vcsws_path.mkdir()
        if not self.manifest_path.exists():
            with open(self.manifest_path, 'w') as file:
                file.write(get_default_manifest())
        if not (self.vcsws_path / 'branches').exists():
            (self.vcsws_path / 'branches').mkdir()
        self.make_new_branch('main')

        # open manifest
        with open(self.manifest_path, 'rb') as file:
            self.manifest = tomllib.load(file)

    def load_ignore(self):
        # open ignore file
        self.ignore_list = [self.vcsws_path]
        if 'vcswsignore' in self.manifest:
            vcswsignore = Path(os.path.join(self.vcsws_path, self.manifest['vcswsignore']))
            if vcswsignore.exists():
                with open(vcswsignore, 'r') as file:
                    for line in file.readlines():
                        line = line.strip()
                        if len(line) != 0:
                            to_ignore = self.project_root / line
                            self.ignore_list += [to_ignore] if to_ignore.exists() else []

    def hash_it(self, rel_path: Path):
        path = self.project_root / rel_path
        if path in self.ignore_list:
            return tuple()

        if path.is_file():
            with open(path, 'rb') as file:
                file_hash = hashlib.sha256(file.read())
                file_hash.update(rel_path.name.encode())
                return ((file_hash.hexdigest(), rel_path.as_posix()), )

        elif path.is_dir():
            res = []
            for sub_path in os.listdir(path):
                res += self.hash_it(Path(rel_path) / sub_path)
            return res

        else:
            raise TypeError(f'Invalid file type')

    def prompt(self, message: str = "") -> str:
        return input(f"[{self.get_project_name()}-{self.branch}]: {message}")

    #
    # GETTERS
    #
    def get_project_name(self):
        if 'project_name' not in dir(self):
            return 'unknown'
        else:
            return self.project_name

    def get_branches(self):
        return os.listdir(self.vcsws_path / 'branches')

    #
    # CLI
    #
    def run_cli(self):
        while True:
            match self.prompt():
                case 'init':
                    self.logger(self.init, self.prompt("Enter project path: "))
                    self.initialized = True

                case 'status':
                    initialize_executor(
                        self.logger,
                        self.initialized,
                        self.status,
                    )

                case 'pull':
                    initialize_executor(
                        asyncio.run,
                        self.initialized,
                        self.pull(self.prompt("Enter address: "))
                    )

                case 'push':
                    initialize_executor(
                        asyncio.run,
                        self.initialized,
                        self.push(self.prompt("Enter address: "))
                    )

                case 'deploy':
                    initialize_executor(
                        asyncio.run,
                        self.initialized,
                        self.deploy()
                    )
                case 'ignore':
                    initialize_executor(
                        self.logger,
                        self.initialized,
                        self.ignore, self.prompt("Enter ignore object: ")
                    )
                case 'profile':
                    initialize_executor(
                        self.logger,
                        self.initialized,
                        lambda: pprint.pprint(self.logger.get_profiler())
                    )
                case 'exit':
                    break

            # checkpoint
            if self.save:
                with open("./vcsws.pickle", "wb") as f:
                    pickle.dump(self, f)


__all__ = [
    'VCSWS'
]
