
from attrs import frozen, field, Factory
from typing import Callable, Protocol, Literal
from logging import Handler, Formatter, StreamHandler, debug, LogRecord
from collections import deque
from twisted.python.log import PythonLoggingObserver, startLogging

def redact_private(record: LogRecord) -> None:
    """
    Redact private information in the given log record, in-place.
    """
    pass


@frozen
class PivacyFilter:
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
    def __init__(self, deque: collections.deque) -> None:
        super().__init__()
        self.deque = deque

    def emit(self, record: logging.LogRecord) -> None:
        self.deque.append(self.format(record))


class LogFormatter(Formatter):
    def formatTime(
        self, record: logging.LogRecord, datefmt: Optional[str] = None
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

    def integrate_privacy_configuration(self, explicit: bool, private: bool) -> None:
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
                    self.logger.removeFilter(self.filter)

    def _is_explicit_change(self, new_explicit: bool) -> bool:
        """
        Determine whether the configuration is changing in a way that is
        allowed with respect to the explicitness or implicitness of the
        existing and new configurations.

        Settings are never allowed to become less explicit but they can remain
        the same level of explicitness or become more explicit.
        """
        return (
            # A new explicit setting can override an existing explicit
            # setting.
            (self.explicit and new_explicit)
            # Any new setting can override an existing implicit setting.
            or not self.explicit
        )

    def is_privacy_change(self, new_private: bool) -> bool:
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

    :ivar handler: A logging Handler which will be given a formatter and added
        to the top-level logger.
    """
    handler: Handler

    def start(self) -> None:
        """
        Set up this logging mode.  This is called early in the lifetime of
        the process.
        """


class FileMode:
    """
    A logging mode where log records are written to an output file.
    """
    outfile: IO[str]
    handler: Handler = field()

    @handler.default
    def _handler_default(self) -> StreamHandler:
        return StreamHandler(stream=self.outfile)

    def start(self) -> None:
        startLogging(self.outfile)


class MemoryMode:
    """
    A logging mode where log records are buffered in a bounded deque.
    """
    logs: deque[LogRecord]
    handler: Handler = field()
    observer: PythonLoggingObserver = Factory(PythonLoggingObserver)

    @handler.default
    def _handler_default(self) -> DequeHandler:
        return DequeHandler(self.logs)

    def start(self) -> None:
        self.observer.start()


class LogMode(Enum):
    stdout = auto()
    in_memory = auto()


def initialize_logger(privacy: LogPrivacy, mode: LogMode) -> None:
    fmt = "%(asctime)s %(levelname)s %(funcName)s %(message)s"
    handler = mode.handler
    handler.setFormatter(LogFormatter(fmt=fmt))

    logger = privacy.logger
    logger.addHandler(handler)
    logger.setLevel(DEBUG)

    mode.start()
    debug("Hello World!")
