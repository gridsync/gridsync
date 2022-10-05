from logging import NullHandler
from logging.handlers import RotatingFileHandler
from pathlib import Path

import pytest

from gridsync import APP_NAME
from gridsync.log import (
    LOGGING_BACKUP_COUNT,
    LOGGING_ENABLED,
    LOGGING_MAX_BYTES,
    LOGS_PATH,
    MultiFileLogger,
    NullLogger,
    make_file_logger,
    read_log,
)


def test_logs_path_is_set():
    """
    During test, LOGS_PATH points to the .logs dir specified by tox.ini
    """
    assert LOGS_PATH.name == ".logs"


@pytest.mark.parametrize(
    "constant, type_",
    [
        (LOGS_PATH, Path),
        (LOGGING_ENABLED, bool),
        (LOGGING_BACKUP_COUNT, int),
        (LOGGING_MAX_BYTES, int),
    ],
)
def test_constant_types(constant, type_):
    """
    The module-level contants exist and are of the expected type
    """
    assert isinstance(LOGGING_BACKUP_COUNT, int)


def test_make_file_logger_returns_rotating_file_handler_by_default():
    logger = make_file_logger("test_rotating_file_handler")
    assert len(logger.handlers) == 1
    assert isinstance(logger.handlers[0], RotatingFileHandler)


def test_make_file_logger_returns_null_handler_if_use_null_handler_is_true():
    logger = make_file_logger("test_null_handler", use_null_handler=True)
    assert len(logger.handlers) == 1
    assert isinstance(logger.handlers[0], NullHandler)


def test_make_file_logger_uses_app_name_for_log_path_if_name_is_none():
    logger = make_file_logger(None)
    assert Path(logger.handlers[0].baseFilename).name == f"{APP_NAME}.log"


def test_make_file_logger_max_bytes():
    max_bytes = 123456789
    logger = make_file_logger("test_max_bytes", max_bytes=max_bytes)
    assert logger.handlers[0].maxBytes == max_bytes


def test_make_file_logger_backup_count():
    backup_count = 123
    logger = make_file_logger("test_backup_count", backup_count=backup_count)
    assert logger.handlers[0].backupCount == backup_count


def test_make_file_logger_fmt():
    name = "test_make_file_logger_fmt"
    p = Path(LOGS_PATH, f"{name}.log")
    p.unlink(missing_ok=True)
    logger = make_file_logger(name, fmt="FMT %(message)s")
    logger.debug("test")
    assert read_log(p).strip() == "FMT test"


def test_log_formatter_uses_utc_timezone():
    name = "test_log_formatter_uses_utc_timezone"
    p = Path(LOGS_PATH, f"{name}.log")
    p.unlink(missing_ok=True)
    logger = make_file_logger(name)
    logger.debug("test")
    assert read_log(p).split(" ")[0].split("+")[-1] == "00:00"


def test_read_log_returns_empty_string_if_file_not_found():
    p = Path("this", "path", "does", "not", "exist")
    p.unlink(missing_ok=True)
    assert read_log(p) == ""


def test_multi_file_logger_write():
    basename = "test_multi_file_logger_write"
    logger_name = "writer"
    logger = MultiFileLogger(basename)
    logger.log(logger_name, "write_test_contents")
    p = Path(LOGS_PATH, f"{basename}.{logger_name}.log")
    assert p.read_text("utf-8").strip().endswith("write_test_contents")


def test_multi_file_logger_read():
    basename = "test_multi_file_logger_read"
    logger_name = "reader"
    p = Path(LOGS_PATH, f"{basename}.{logger_name}.log")
    p.write_text("read_test_contents")
    logger = MultiFileLogger(basename)
    assert logger.read_log(logger_name).strip().endswith("read_test_contents")


def test_multi_file_logger_omit_fmt():
    basename = "test_multi_file_logger_omit_fmt"
    logger_name = "omit_fmt"
    logger = MultiFileLogger(basename)
    Path(LOGS_PATH, f"{basename}.{logger_name}.log").unlink(missing_ok=True)
    logger.log(logger_name, "omit_fmt_contents", omit_fmt=True)
    assert logger.read_log(logger_name).strip() == "omit_fmt_contents"


def test_null_logger():
    logger = NullLogger()
    logger.log("null_logger_test", "test")
    logger.read_log("null_logger_test") == ""
