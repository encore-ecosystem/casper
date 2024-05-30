import os
import re
import pprint
import pickle
import tomllib
import hashlib
import asyncio
import datetime
import websockets


from pathlib import Path
from src.logger import Logger
from src.utils import get_default_manifest, initialize_executor, safe_touch


class VCSWS:
    project_root  : Path
    vcsws_path    : Path
    manifest_path : Path
    project_name  : str
    ignore        : list
    branch        : str  = 'main'

    #
    # MAGIC
    #
    def __init__(self, logger: Logger, save_progress: bool = False):
        self.logger      = logger
        self.save        = save_progress
        self.initialized = False

    def __str__(self) -> str:
        return f'[{self.get_project_name()}]'

    #
    # INTERFACE
    #
    def init(self, project_path):
        project_root = Path(project_path).absolute()
        if not project_root.exists() or not project_root.is_dir():
            print('[Error] Project path invalid')
            return

        self.project_root  = project_root
        self.vcsws_path    = self.project_root / '.vcsws'
        self.manifest_path = self.vcsws_path   / 'manifest.toml'
        self.project_name  = self.project_root.name

        self.load_manifest()
        self.load_ignore()

    def make_new_branch(self, branch_name: str):
        if not (self.vcsws_path / 'branches' /  branch_name).exists():
            (self.vcsws_path / 'branches' / branch_name).mkdir()

    def relocate(self, branch_name: str):
        if branch_name in os.listdir(self.vcsws_path / 'branches'):
            self.branch = branch_name

    def status(self):
        self.logger(self.load_ignore)
        hashes = self.logger(self.hash_it, self.vcsws_path.parent)
        for h in hashes:
            print(h)
        print(self.ignore)

    def commit(self, commit_name: str, commit_description: str):
        if len(commit_name) == 0:
            print('[Error]: Please, enter a non-empty commit name')
        else:
            with open(self.vcsws_path / 'branches' / self.branch / commit_name, 'w') as commit_file:
                commit_file.write(commit_description + '\n')

                for hash_, file_path in self.hash_it(self.vcsws_path.parent):
                    commit_file.write(f"{hash_} : {file_path}\n")

    async def push(self, address: str):
        async with websockets.connect(address) as ws:
            await ws.send("push main")

    async def pull(self, address: str):
        async with websockets.connect(address) as ws:
            await ws.send("pull main")

    async def deploy(self):
        deploy_is_running = True

        async def handler(websocket: websockets.WebSocketServerProtocol, path):
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
        self.ignore = []
        if 'vcswsignore' in self.manifest:
            topyignore = Path(os.path.join(self.vcsws_path, self.manifest['vcswsignore']))
            if topyignore.exists():
                with open(topyignore, 'r') as file:
                    for line in file.readlines():
                        to_ignore = self.project_root / line.strip()
                        self.ignore += [to_ignore] if to_ignore.exists() else []

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

                case 'make_new_branch':
                    initialize_executor(
                        self.logger,
                        self.initialized,
                        self.make_new_branch, self.prompt("Enter branch name: ")
                    )

                case 'status':
                    initialize_executor(
                        self.logger,
                        self.initialized,
                        self.status,
                    )

                case 'commit':
                    initialize_executor(
                        self.logger,
                        self.initialized,
                        self.prompt("Enter commit name: "), self.prompt("Enter commit description: ")
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

                case 'branches':
                    branches = initialize_executor(
                        self.logger,
                        self.initialized,
                        self.get_branches
                    )
                    for branch in branches:
                        print(f" - {branch}")

                case 'relocate':
                    initialize_executor(
                        self.logger,
                        self.initialized,
                        self.relocate, self.prompt("Enter target branch name:")
                    )

                case 'deploy':
                    initialize_executor(
                        asyncio.run,
                        self.initialized,
                        self.deploy
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