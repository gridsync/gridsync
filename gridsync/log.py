import collections
import logging
import sys
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional

from twisted.python.log import PythonLoggingObserver, startLogging

from gridsync import APP_NAME, config_dir


class LogFormatter(logging.Formatter):
    def formatTime(
        self, record: logging.LogRecord, datefmt: Optional[str] = None
    ) -> str:
        return datetime.now(timezone.utc).isoformat()


class DequeHandler(logging.Handler):
    def __init__(self, deque: collections.deque) -> None:
        super().__init__()
        self.deque = deque

    def emit(self, record: logging.LogRecord) -> None:
        self.deque.append(self.format(record))


def initialize_logger(
    log_deque: collections.deque, to_stdout: bool = False
) -> None:
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    formatter = LogFormatter(
        fmt="%(asctime)s %(levelname)s %(funcName)s %(message)s"
    )

    deque_handler = DequeHandler(log_deque)
    deque_handler.setFormatter(formatter)
    logger.addHandler(deque_handler)

    log_path = Path(config_dir, "logs", f"{APP_NAME}.log")
    log_path.parent.mkdir(parents=True, exist_ok=True)
    file_handler = RotatingFileHandler(
        log_path, maxBytes=10_000_000, backupCount=10
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    if to_stdout:
        stdout_handler = logging.StreamHandler(stream=sys.stdout)
        stdout_handler.setFormatter(formatter)
        logger.addHandler(stdout_handler)
        startLogging(sys.stdout)

    observer = PythonLoggingObserver()
    observer.start()
    logging.debug("Hello World!")
