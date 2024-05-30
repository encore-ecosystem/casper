import os

from src.vcsws_core import *
from src.utils      import *
from src.logger     import *
from pathlib        import Path


def main():
    vcsws_root_path = Path().absolute()
    logger_path     = vcsws_root_path / 'logs'

    do_log = False
    if do_log:
        safe_mkdir(logger_path)
    logger = Logger(logger_path, terminal_mirror=False, do_log=do_log)

    vcsws  = logger.run(VCSWS, logger)
    if ".vcsws" in os.listdir(os.curdir):
        vcsws.init(".")
        vcsws.initialized = True

    vcsws.run_cli()


if __name__ == '__main__':
    main()