import os
import tqdm
import json
import tomllib
import hashlib
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
        self.vcsws_server                       = '127.0.0.1:6969' # todo remove

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

    async def sync(self):
        # Get address of VCSWS server
        print("Connecting to vcsws server...")
        if self.vcsws_server is None:
            self.vcsws_server = input("Enter address:port of vcsws server: ws://")
        else:
            opt = input(f"Is address of VCSWS server right?: {self.vcsws_server} (y=default/n)").strip().lower()
            if opt not in ('', 'y', 'yes'):
                self.vcsws_server = input("Enter address:port of vcsws server: ws://")

        # sync
        async with websockets.connect(f"ws://{self.vcsws_server}") as ws:
            await ws.send("sync")
            to_send = self.logger(self.hash_it, Path())
            data = {}
            for (hash_, path_) in to_send:
                data[hash_] =  path_

            await ws.send(json.dumps(data))

            to_download = json.loads(await ws.recv())
            for file_hash in tqdm.tqdm(to_download):
                with open(self.project_root / data[file_hash], 'rb') as binfile:
                    await ws.send(binfile.read())

    async def sub(self):
        # Get address of VCSWS server
        print("Connecting to vcsws server...")
        if self.vcsws_server is None:
            self.vcsws_server = input("Enter address:port of vcsws server: ws://")
        else:
            opt = input(f"Is address of VCSWS server right?: {self.vcsws_server} (y=default/n)").strip().lower()
            if opt not in ('', 'y', 'yes'):
                self.vcsws_server = input("Enter address:port of vcsws server: ws://")

        # Try to connect
        server_ws = await websockets.connect(f"ws://{self.vcsws_server}")

        # Send subscribe msg
        await server_ws.send("subscribe")

        # Wait to receive data
        print("Waiting sync operator...")
        server_hash_to_path = json.loads(await server_ws.recv())
        server_path_to_hash = reverse_dict(server_hash_to_path)

        client_hash_to_path = {}
        client_path_to_hash = {}
        for (hash_, file_path) in self.hash_it(Path()):
            client_hash_to_path[hash_] = file_path
            client_path_to_hash[file_path] = hash_

        to_download = {}
        # compare hashes
        while len(server_hash_to_path) > 0:
            server_hash, server_path = server_hash_to_path.popitem()
            if server_hash in client_hash_to_path:
                # case 1: file has the different path
                if client_hash_to_path[server_hash] != server_path:
                    print(f"[M] File moved to new destination ![NOT IMPLEMENTED]")
                    print(f"\tFROM: {client_hash_to_path[server_hash]} TO: {server_path}")
                    # todo implement handler
                del client_hash_to_path[server_hash]
            else:
                # case 2: file updated
                if server_path in client_path_to_hash:
                    client_path = client_path_to_hash[server_path]
                    print(f"[U] File updated: {client_path}")
                    to_download[server_hash] = server_path
                # case 3: new file
                else:
                    print(f"[N] New file: {server_path}")
                    to_download[server_hash] = server_path
        for hash_ in client_hash_to_path:
            print(f"[D] File deleted: {client_hash_to_path[hash_]}")

        # push request
        await server_ws.send(json.dumps(to_download))

        # download new files
        server_hash_to_path = reverse_dict(server_path_to_hash)
        for hash_ in tqdm.tqdm(to_download):
            binfile = await server_ws.recv()
            safe_mkdir((self.project_root / server_hash_to_path[hash_]).parent)
            with open(self.project_root / server_hash_to_path[hash_], 'wb') as f:
                f.write(binfile)

        await server_ws.close()

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




__all__ = [
    'VCSWS'
]
