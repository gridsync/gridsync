import collections
import logging
import sys
from datetime import datetime, timezone
from typing import Optional

from twisted.python.log import PythonLoggingObserver, startLogging


class DequeHandler(logging.Handler):
    def __init__(self, deque: collections.deque) -> None:
        super().__init__()
        self.deque = deque

    def emit(self, record: logging.LogRecord) -> None:
        self.deque.append(self.format(record))


class LogFormatter(logging.Formatter):
    def formatTime(
        self, record: logging.LogRecord, datefmt: Optional[str] = None
    ) -> str:
        return datetime.now(timezone.utc).isoformat()


def initialize_logger(
    log_deque: collections.deque, to_stdout: bool = False
) -> None:
    deque_handler = DequeHandler(log_deque)
    observer = PythonLoggingObserver()
    observer.start()
    formatter = LogFormatter(
        fmt="%(asctime)s %(levelname)s %(funcName)s %(message)s"
    )
    deque_handler.setFormatter(formatter)
    logger = logging.getLogger()
    logger.addHandler(deque_handler)
    if to_stdout:
        stdout_handler = logging.StreamHandler(stream=sys.stdout)
        startLogging(sys.stdout)
        stdout_handler.setFormatter(formatter)
        logger.addHandler(stdout_handler)
    logger.setLevel(logging.DEBUG)
    logging.debug("Hello World!")