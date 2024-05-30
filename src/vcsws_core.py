import os
import re
import pickle
import tomllib
import hashlib
import asyncio
import datetime
import websockets

from pathlib import Path
from src.logger import Logger


class VCSWS:
    project_root  : Path
    topy_path     : Path
    manifest_path : Path
    project_name  : str
    ignore        : list
    branch        : str  = 'main'
    SAVE_PROGRESS : bool = False

    def __init__(self, logger: Logger):
        self.logger = logger

    def init(self, project_path):
        project_root = Path(project_path).absolute()
        if not project_root.exists() or not project_root.is_dir():
            print('[Error] Project path invalid')
            return

        project_name = os.path.basename(project_path)

        self.project_root  = Path(os.path.join(".", project_name))
        self.topy_path     = self.project_root / '.vcsws'
        self.manifest_path = self.topy_path / 'manifest.toml'
        self.project_name  = self.project_root.name

        self.load_manifest()
        self.load_ignore()

    def load_manifest(self):
        # Check existing of the project manifest
        if not self.topy_path.exists():
            self.topy_path.mkdir()
        if not self.manifest_path.exists():
            with open(self.manifest_path, 'w') as file:
                file.write(self.get_default_manifest(self.topy_path))
        if not (self.topy_path / 'branches').exists():
            (self.topy_path / 'branches').mkdir()
        self.make_new_branch('main')

        # open manifest
        with open(self.manifest_path, 'rb') as file:
            self.manifest = tomllib.load(file)

    def load_ignore(self):
        # open ignore file
        self.ignore = [Path(self.topy_path)]
        if 'topyignore' in self.manifest:
            topyignore = Path(os.path.join(self.topy_path, self.manifest['topyignore']))
            if topyignore.exists():
                with open(topyignore, 'r') as file:
                    for line in file.readlines():
                        to_ignore = self.project_root / line.strip()
                        self.ignore += [to_ignore] if to_ignore.exists() else []

    def make_new_branch(self, branch_name: str):
        if not (self.topy_path / 'branches' /  branch_name).exists():
            (self.topy_path / 'branches' / branch_name).mkdir()

    def relocate(self, branch_name: str):
        if branch_name in os.listdir(self.topy_path / 'branches'):
            self.branch = branch_name

    def hash_it(self, path: Path):
        if path in self.ignore:
            return []

        if path.is_file():
            with open(path, 'rb') as file:
                file_hash = hashlib.sha256(file.read()).hexdigest()
                return [(file_hash, path)]

        elif path.is_dir():
            res = []
            for sub_path in path.iterdir():
                res += self.hash_it(sub_path)
            return res

        else:
            raise TypeError(f'Invalid file type')

    def status(self):
        hashes = self.hash_it(self.topy_path.parent)
        for h in hashes:
            print(h)

    def commit(self, commit_name: str, commit_description: str):
        if len(commit_name) == 0:
            print('[Error]: Please, enter a non-empty commit name')
        else:
            with open(self.topy_path / 'branches' / self.branch / commit_name, 'w') as commit_file:
                commit_file.write(commit_description + '\n')

                for hash_, file_path in self.hash_it(self.topy_path.parent):
                    commit_file.write(f"{hash_} : {file_path}\n")

    async def push(self, address: str):
        async with websockets.connect(address) as ws:
            await ws.send("push main")

    async def pull(self, address: str):
        async with websockets.connect(address) as ws:
            await ws.send("pull main")

    async def deploy(self):
        deploy_is_running = True

        async def handler(websocket: websockets.WebSocketClientProtocol, path):
            print(f"[{datetime.datetime.now()}] New connection from {websocket.remote_address}")
            command = await websocket.recv()
            nonlocal deploy_is_running
            if   re.fullmatch(r"pull \w+", command):
                print('pulling', command)
                deploy_is_running = False
            elif re.fullmatch(r"push \w+", command):
                print('pushing', command)
                deploy_is_running = False
            else:
                print('unexpected command', command)

        async with websockets.serve(handler, '127.0.0.1', int(self.prompt("enter port: "))) as server:
            print(f"[{datetime.datetime.now()}] Starting server...")
            while deploy_is_running:
                await asyncio.sleep(5)
                print(f"[server status]: Ok")

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
        return os.listdir(self.topy_path / 'branches')

    @classmethod
    def get_default_manifest(cls, project_path):
        return (f'project_name="test"\n'
                f'authors="test"\n'
                f'topy_version="0.0.1"\n')

    #
    # SETTERS
    #

    #
    # MAGIC
    #
    def __str__(self) -> str:
        return f'[{self.get_project_name()}]'

    #
    # CLI
    #
    def run_cli(self):
        while True:
            req = self.prompt()
            match req:
                case 'init':
                    self.logger(self.init, self.prompt("Enter project path: "))

                case 'make_new_branch':
                    self.logger(self.make_new_branch, self.prompt("Enter branch name: "))

                case 'status':
                    self.logger(self.status)

                case 'commit':
                    self.logger(
                        self.commit,
                        self.prompt("Enter commit name: "), self.prompt("Enter commit description: ")
                    )

                case 'pull':
                    asyncio.run(
                        self.pull(self.prompt("Enter address: "))
                    )

                case 'push':
                    asyncio.run(
                        self.push(self.prompt("Enter address: "))
                    )

                case 'branches':
                    branches = self.logger(self.get_branches)
                    for branch in branches:
                        print(f" - {branch}")

                case 'relocate':
                    self.logger(self.relocate, self.prompt("Enter target branch name:"))

                case 'deploy':
                    asyncio.run(self.deploy())

                case 'exit':
                    break

            # checkpoint
            if self.SAVE_PROGRESS:
                with open("./vcsws.pickle", "wb") as f:
                    pickle.dump(self, f)


__all__ = [
    'VCSWS'
]