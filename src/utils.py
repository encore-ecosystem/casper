from pathlib import Path
import configparser


def safe_mkdir(path: Path):
    if not path.exists():
        path.mkdir(parents=True)
        return True
    return False


def safe_touch(path: Path):
    if not path.exists():
        path.touch()
        return True
    return False


def get_default_config():
    config = configparser.ConfigParser()
    config.add_section('cache')
    config.set('cache', 'save_progress', str(True))

    return config


def get_default_manifest():
    return (f'project_name="test"\n'
            f'authors="test"\n'
            f'vcsws_version="0.0.1"\n'
            f'vcswsignore=".vcswsignore"\n'
            )


def checkpoint_for_config(path: Path, config: configparser.ConfigParser):
    with open(path, 'w') as f:
        config.write(f)


def initialize_executor(func, initialized: bool = False, *args, **kwargs):
    if initialized:
        return func(*args, **kwargs)
    else:
        print("Please initialize the project first")


__all__ = [
    'safe_mkdir',
    'safe_touch',
    'get_default_config',
    'get_default_manifest',
    'checkpoint_for_config',
    'initialize_executor',
]