import datetime


def info(msg: str):
    print(
        f"[{datetime.datetime.now()}] [INFO]: {msg}"
    )


__all__ = [
    'info'
]