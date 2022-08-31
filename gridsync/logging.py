from argparse import Namespace
from collections import deque
from datetime import datetime, timezone
from logging import (
    DEBUG,
    Filter,
    Formatter,
    Handler,
    Logger,
    LogRecord,
    StreamHandler,
    debug,
    getLogger,
)
from typing import IO, Literal, Optional, Protocol

from attrs import Factory, define, field, frozen
from twisted.python.log import PythonLoggingObserver, startLogging


def redact_private(_: LogRecord) -> None:
    """
    Redact private information in the given log record, in-place.
    """


@frozen
class PrivacyFilter(Filter):
    """
    A stdlib logging filter which modifies log records in-place to redact
    sensitive information.
    """

    def filter(self, record: LogRecord) -> Literal[True]:
        """
        Redact any private information in the given log record.
        """
        redact_private(record)
        return True


class DequeHandler(Handler):
    """
    Record log records in a ``deque``.
    """
    log_deque: deque[str]

    def __init__(self, log_deque: deque[str]) -> None:
        super().__init__()
        self.log_deque = log_deque

    def emit(self, record: LogRecord) -> None:
        # TODO Consider delaying formatting until we actually need the string
        # to avoid unnecessary formatting work.
        self.log_deque.append(self.format(record))


class LogFormatter(Formatter):
    """
    Format the time component of records using ISO8601.
    """
    def formatTime(
        self, record: LogRecord, datefmt: Optional[str] = None
    ) -> str:
        return datetime.now(timezone.utc).isoformat()


@define
class LogPrivacy:
    """
    Represent the desired degree of privacy preserved by log events
    recorded by the system.

    :ivar logger: A logging object to which to propagate the privacy
        configuration.

    :ivar _explicit: See ``integrate_privacy_configuration``

    :ivar _private: See ``integrate_privacy_configuration``

    :ivar _filter: A logging filter which implements the log privacy behavior.
    """

    logger: Logger

    _explicit: bool = False
    _private: bool = False
    _filter: Filter = Factory(PrivacyFilter)

    def integrate_privacy_configuration(
        self, explicit: bool, private: bool
    ) -> None:
        """
        Account for new information about how logging privacy should be configured.

        The new configuration does not *necessarily* replace the existing
        configuration.  It can only replace existing configuration if it
        reflects at least as much intention on the part of a user as the old
        configuration reflected.

        :param explicit: Does this configuration represent an explicit choice
            by a user?

        :param private: Should the new privacy configuration be "private" or
            not ("exposed")?
        """
        if self._is_explicit_change(explicit):
            self._explicit = explicit
            if self._is_privacy_change(private):
                self._private = private
                if self._private:
                    self.logger.addFilter(self._filter)
                else:
                    self.logger.removeFilter(self._filter)

    def _is_explicit_change(self, new_explicit: bool) -> bool:
        """
        Determine whether the configuration is changing in a way that is
        allowed with respect to the explicitness or implicitness of the
        existing and new configurations.

        Settings are never allowed to become less explicit but they can remain
        the same level of explicitness or become more explicit.
        """
        return (  # pylint: disable=consider-using-ternary
            # A new explicit setting can override an existing explicit
            # setting.
            (self._explicit and new_explicit)
            # Any new setting can override an existing implicit setting.
            or not self._explicit
        )

    def _is_privacy_change(self, new_private: bool) -> bool:
        """
        Determine whether the actual privacy setting is changing between
        the existing configuration and a new configuration.  This determines
        whether the configuration change might need to be propagated to other
        parts of the system (specifically, the logging configuration).
        """
        return self._private != new_private


class LogMode(Protocol):
    """
    An object which defines a certain log handling behavior.
    """

    @property
    def logs(self) -> deque[str]:
        """
        Some recently recorded logs, if they are available.
        """

    @property
    def handler(self) -> Handler:
        """
        A logging Handler which will be given a formatter and added to the
        top-level logger.
        """

    def start(self) -> None:
        """
        Set up this logging mode.  This is called early in the lifetime of
        the process.
        """


@frozen
class FileMode:
    """
    A logging mode where log records are written to an output file.
    """

    outfile: IO[str]
    handler: Handler = field()

    @property
    def logs(self) -> deque[str]:
        """
        Since we haven't kept the log records in memory in this mode, just
        give back an empty list.  Later we could keep some in memory in
        addition to writing them out or require they be written somewhere from
        which we can read them back.
        """
        return deque()

    @handler.default
    def _handler_default(self) -> StreamHandler:
        return StreamHandler(stream=self.outfile)

    def start(self) -> None:
        startLogging(self.outfile)


@frozen
class MemoryMode:
    """
    A logging mode where log records are buffered in a bounded deque.
    """

    maxlen: int
    logs: deque[str] = field()
    handler: Handler = field()
    observer: PythonLoggingObserver = Factory(PythonLoggingObserver)

    @logs.default
    def _logs_default(self) -> deque:
        return deque(maxlen=self.maxlen)

    @handler.default
    def _handler_default(self) -> DequeHandler:
        return DequeHandler(self.logs)

    def start(self) -> None:
        self.observer.start()


def initialize_logger(privacy: LogPrivacy, mode: LogMode) -> None:
    fmt = "%(asctime)s %(levelname)s %(funcName)s %(message)s"
    handler = mode.handler
    handler.setFormatter(LogFormatter(fmt=fmt))

    logger = privacy.logger
    logger.addHandler(handler)
    logger.setLevel(DEBUG)

    mode.start()
    debug("Hello World!")


def initialize_logger_from_args(
    args: Namespace, log_maxlen: int, stdout: IO[str]
) -> tuple[LogPrivacy, LogMode]:
    privacy = LogPrivacy(
        getLogger(),
        # Reflect that the user chose something with a command-line argument.
        explicit="log-privacy" in args,
        # Lacking user choice, default to privacy mode out of an abundance
        # of caution.
        private=args.get("log-privacy", False),
    )

    if "log-to-stdout" in args:
        # XXX We could give file logs a max length too, but as long as we only
        # log to stdout it doesn't make much sense.
        mode: LogMode = FileMode(stdout)
    else:
        mode = MemoryMode(log_maxlen)

    initialize_logger(privacy, mode)

    return privacy, mode
