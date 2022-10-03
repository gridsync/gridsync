import logging
import sys
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional, Union

from twisted.python.log import PythonLoggingObserver, startLogging

from gridsync import APP_NAME, config_dir, settings
from gridsync.util import to_bool

_logging_settings = settings.get("logging", {})

_logging_path = _logging_settings.get("path")
if _logging_path:
    LOGS_PATH = Path(_logging_path)
else:
    LOGS_PATH = Path(config_dir, "logs")

LOGGING_ENABLED = to_bool(_logging_settings.get("enabled", "false"))
LOGGING_MAX_BYTES = int(_logging_settings.get("max_bytes", 10_000_000))
LOGGING_BACKUP_COUNT = int(_logging_settings.get("backup_count", 1))


class LogFormatter(logging.Formatter):
    def formatTime(
        self, record: logging.LogRecord, datefmt: Optional[str] = None
    ) -> str:
        return datetime.now(timezone.utc).isoformat()


def make_file_logger(
    name: Optional[str] = None,
    max_bytes: int = LOGGING_MAX_BYTES,
    backup_count: int = LOGGING_BACKUP_COUNT,
    fmt: Optional[str] = "%(asctime)s %(levelname)s %(funcName)s %(message)s",
    use_null_handler: bool = False,
) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    logger.propagate = False

    LOGS_PATH.mkdir(mode=0o700, parents=True, exist_ok=True)

    if not name:
        name = APP_NAME

    handler: Union[logging.NullHandler, RotatingFileHandler]
    if use_null_handler or not LOGGING_ENABLED:
        handler = logging.NullHandler()
    else:
        handler = RotatingFileHandler(
            Path(LOGS_PATH, f"{name}.log"),
            maxBytes=max_bytes,
            backupCount=backup_count,
        )
    if fmt:
        handler.setFormatter(LogFormatter(fmt=fmt))
    logger.addHandler(handler)
    return logger


def initialize_logger(
    to_stdout: bool = False, use_null_handler: bool = False
) -> None:
    logger = make_file_logger(use_null_handler=use_null_handler)
    formatter = LogFormatter(
        fmt="%(asctime)s %(levelname)s %(funcName)s %(message)s"
    )

    if to_stdout:
        stdout_handler = logging.StreamHandler(stream=sys.stdout)
        stdout_handler.setFormatter(formatter)
        logger.addHandler(stdout_handler)
        startLogging(sys.stdout)

    observer = PythonLoggingObserver()
    observer.start()
    logging.debug("Hello World!")


def read_log(path: Optional[Path] = None) -> str:
    if path is None:
        path = Path(LOGS_PATH, f"{APP_NAME}.log")
    try:
        return path.read_text("utf-8")
    except FileNotFoundError:
        return ""


class MultiFileLogger:
    def __init__(self, basename: str) -> None:
        self.basename = basename
        self._loggers: dict[str, logging.Logger] = {}

    def log(
        self, logger_name: str, message: str, omit_fmt: bool = False
    ) -> None:
        if not LOGGING_ENABLED:
            return
        name = f"{self.basename}.{logger_name}"
        logger = self._loggers.get(name)
        if not logger:
            if omit_fmt:
                logger = make_file_logger(name, fmt=None)
            else:
                logger = make_file_logger(name)
            self._loggers[name] = logger
        logger.debug(message)

    def read_log(self, logger_name: str) -> str:
        return read_log(Path(LOGS_PATH, f"{self.basename}.{logger_name}.log"))


class NullLogger:
    def log(
        self, logger_name: str, message: str, omit_fmt: bool = False
    ) -> None:
        pass

    def read_log(  # pylint: disable=unused-argument
        self, logger_name: str
    ) -> str:
        return ""
