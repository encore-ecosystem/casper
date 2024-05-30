from src.vcsws_core import *
from src.utils      import *
from src.logger     import *
from pathlib        import Path

import configparser
import pickle


def main():
    #
    # 0) Initialize paths
    vcsws_root_path    = Path().absolute()
    vcsws_config_path  = vcsws_root_path / 'vcsws.config'
    pickled_vcsws_path = vcsws_root_path / 'vcsws'
    logger_path        = vcsws_root_path / 'logs'

    #
    # 1) Load logger
    safe_mkdir(logger_path)
    logger = Logger(logger_path)

    #
    # 2) Load VCSWS config
    if safe_touch(vcsws_config_path):
        config = logger.run(get_default_config)
    else:
        config = configparser.ConfigParser()
        logger.run(config.read, vcsws_config_path)
    logger.run(checkpoint_for_config, vcsws_config_path, config)

    #
    # 3) Initialize VCSWS
    if bool(config.get('cache', 'save_progress')):
        if pickled_vcsws_path.exists():
            with open(pickled_vcsws_path, "rb") as f:
                vcsws = logger.run(pickle.load, f)
        else:
            logger.warn("VCSWS pickle file not found")
            vcsws = logger.run(VCSWS, logger)

    #
    # 4) Run VCSWS CLI
    vcsws.run_cli()


if __name__ == '__main__':
    main()
