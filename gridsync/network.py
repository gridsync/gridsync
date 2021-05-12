import errno
import logging
import socket
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
            except socket.error as err:
                logging.debug("Couldn't bind to port %i: %s", port, err)
                if err.errno == errno.EADDRINUSE:
                    port = randint(range_min, range_max)
                    continue
                raise
            logging.debug("Port %s is free", port)
            return port
