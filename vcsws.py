import asyncio
import os


from src.client import *
from src.server import *
from src.cli    import run_cli
from src.utils      import *
from src.logger     import *
from pathlib        import Path


def client(vcsws_root_path: str, do_log: bool = False):
    # Initialize
    vcsws_root_path = Path(vcsws_root_path)
    logger_path     = vcsws_root_path / 'logs'

    # Make logging
    if do_log:
        safe_mkdir(logger_path)
    logger = Logger(logger_path, terminal_mirror=False, do_log=do_log)

    # Run vcsws
    vcsws  = logger.run(VCSWS, logger)
    if ".vcsws" in os.listdir(os.curdir):
        vcsws.init(".")
        vcsws.initialized = True

    run_cli(vcsws)


def server(vcsws_root_path: str, do_log: bool = False, ip: str = None):
    # Initialize
    vcsws_root_path = Path(vcsws_root_path)
    logger_path     = vcsws_root_path / 'logs'

    # Make logging
    if do_log:
        safe_mkdir(logger_path)
    logger = Logger(logger_path, terminal_mirror=False, do_log=do_log)

    # Ip
    if ip is None:
        print("There is no ip pushed in args, server determine public ip itself")
        server_address = get_my_pub_ip()
    else:
        server_address = ip
    print(f'Server will use {server_address}')

    # Run server
    vcsws_server    = VCSWS_Server(
        server_address = server_address,
        server_port    = '6969'
    )
    asyncio.run(vcsws_server.run())


if __name__ == '__main__':
    import sys
    args = sys.argv
    if '-s' in args:
        # run server
        server(args[0], '-l' in args)
    else:
        # run client
        client(args[0], '-l' in args)
