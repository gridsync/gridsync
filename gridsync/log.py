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


def make_file_logger(
    name: Optional[str] = None,
    max_bytes: int = 10_000_000,
    backup_count: int = 10,
    fmt: Optional[str] = "%(asctime)s %(levelname)s %(funcName)s %(message)s",
) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    logger.propagate = False

    logs_path = Path(config_dir, "logs")
    logs_path.mkdir(mode=0o700, parents=True, exist_ok=True)

    if not name:
        name = APP_NAME

    handler = RotatingFileHandler(
        Path(logs_path, f"{name}.log"),
        maxBytes=max_bytes,
        backupCount=backup_count,
    )
    if fmt:
        handler.setFormatter(LogFormatter(fmt=fmt))
    logger.addHandler(handler)
    return logger


def initialize_logger(
    log_deque: collections.deque, to_stdout: bool = False
) -> None:
    logger = make_file_logger()
    formatter = LogFormatter(
        fmt="%(asctime)s %(levelname)s %(funcName)s %(message)s"
    )

    deque_handler = DequeHandler(log_deque)
    deque_handler.setFormatter(formatter)
    logger.addHandler(deque_handler)

    if to_stdout:
        stdout_handler = logging.StreamHandler(stream=sys.stdout)
        stdout_handler.setFormatter(formatter)
        logger.addHandler(stdout_handler)
        startLogging(sys.stdout)

    observer = PythonLoggingObserver()
    observer.start()
    logging.debug("Hello World!")


def read_log_messages(path: Path) -> list[str]:
    try:
        return [line for line in path.read_text("utf-8").split("\n") if line]
    except FileNotFoundError:
        return []


class MultiFileLogger:
    def __init__(self, basename: str) -> None:
        self.basename = basename
        self._loggers: dict[str, logging.Logger] = {}

    def log(
        self, logger_name: str, message: str, omit_fmt: bool = False
    ) -> None:
        name = f"{self.basename}.{logger_name}"
        logger = self._loggers.get(name)
        if not logger:
            if omit_fmt:
                logger = make_file_logger(name, fmt=None)
            else:
                logger = make_file_logger(name)
            self._loggers[name] = logger
        logger.debug(message)

    def _find_log_files(self, logger_name: str) -> list[Path]:
        logs_path = Path(config_dir, "logs")
        return sorted(logs_path.glob(f"{self.basename}.{logger_name}.log*"))

    def read_messages(self, logger_name: str) -> list[str]:
        messages = []
        for p in self._find_log_files(logger_name):
            messages.extend(read_log_messages(p))
        return messages
