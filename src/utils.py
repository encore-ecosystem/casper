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
    num_of_saved_projects = 5

    config = configparser.ConfigParser()
    config.add_section('cache')
    config.set('cache', 'save_progress', str(True))

    return config


def checkpoint_for_config(path: Path, config: configparser.ConfigParser):
    with open(path, 'w') as f:
        config.write(f)


__all__ = [
    'safe_mkdir',
    'safe_touch',
    'get_default_config',
    'checkpoint_for_config',
]