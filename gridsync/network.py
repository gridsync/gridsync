import errno
import logging
import socket
import sys
from random import randint


def get_local_network_ip() -> str:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    s.connect(("10.255.255.255", 1))
    ip = s.getsockname()[0]
    s.close()
    return ip


def get_free_port(
    port: int = 0, range_min: int = 49152, range_max: int = 65535
) -> int:
    if not port:
        port = randint(range_min, range_max)
    while True:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                logging.debug("Trying to bind to port: %i", port)
                s.bind(("127.0.0.1", port))
            except OSError as err:
                logging.debug("Couldn't bind to port %i: %s", port, err)
                if err.errno == errno.EADDRINUSE or (
                    # "[WinError 10013] An attempt was made to access a
                    # socket in a way forbidden by its access
                    # permissions"
                    sys.platform == "win32"
                    and err.winerror == 10013
                ):
                    port = randint(range_min, range_max)
                    continue
                raise
            logging.debug("Port %s is free", port)
            return port
