from datetime import datetime
from pathlib import Path
import logging
import os
import time


class Logger:
    def __init__(self, log_dir: Path, terminal_mirror: bool = True, num_of_saved_logs: int = 5, profiler: bool = True):
        self.mirror       = terminal_mirror
        self.use_profiler = profiler
        self.profiler     = {}

        logging.basicConfig(
            level    = logging.INFO,
            filename = log_dir / datetime.now().strftime("%Y_%m_%d %H_%M_%S.log"),
            filemode = "w",
            format   = "[%(asctime)s] [%(levelname)s]: %(message)s"
        )

        # delete old log files
        all_logs    = sorted(os.listdir(log_dir), reverse=True)
        num_of_logs = len(all_logs)
        while num_of_logs > num_of_saved_logs:
            os.remove(log_dir / all_logs.pop())
            num_of_logs -= 1

    def debug(self, message: str):
        if self.mirror:
            print(f"[{datetime.now()}] [DEBUG]: {message}")
        logging.debug(message)

    def info(self, message: str):
        if self.mirror:
            print(f"[{datetime.now()}] [INFO]: {message}")
        logging.info(message)

    def warn(self, message: str):
        if self.mirror:
            print(f"[{datetime.now()}] [WARN]: {message}")
        logging.warning(message)

    def error(self, message: str):
        if self.mirror:
            print(f"[{datetime.now()}] [ERRR]: {message}")
        logging.error(message)

    def critical(self, message: str):
        if self.mirror:
            print(f"[{datetime.now()}] [CRIT]: {message}")
        logging.critical(message)

    def run(self, func, *args, **kwargs):
        self.info(f"run <{func.__name__:^36}> with args: <{args}> kwargs: <{kwargs}>")

        start = time.time()
        result = func(*args, **kwargs)
        if self.use_profiler:
            if func.__name__ in self.profiler:
                self.profiler[func.__name__]['calls'] += 1
                self.profiler[func.__name__]['total_time'] += time.time() - start
            else:
                self.profiler[func.__name__] = {'calls':  1,  'total_time':  time.time() - start}
        return result

    def get_profiler(self):
        return self.profiler

    __call__ = run


__all__ = [
    'Logger'
]
