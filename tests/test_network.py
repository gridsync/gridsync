import socket
from ipaddress import IPv4Address, IPv6Address, ip_address
from unittest.mock import Mock

import pytest

from gridsync.network import get_free_port, get_local_network_ip


def test_get_local_network_ip_returns_str():
    assert isinstance(get_local_network_ip(), str)


def test_get_local_network_ip_is_ip_address():
    address = ip_address(get_local_network_ip())
    assert type(address) in (IPv4Address, IPv6Address)


def test_get_free_port_returns_int():
    assert isinstance(get_free_port(), int)


def test_get_free_port_is_random():
    assert get_free_port() != get_free_port()


def test_get_free_port_with_port_in_use():
    occupied_port = get_free_port()
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", occupied_port))
        free_port = get_free_port(occupied_port)
        assert free_port != occupied_port


def test_get_free_port_raise_error(monkeypatch):
    monkeypatch.setattr("socket.socket.bind", Mock(side_effect=OSError))
    with pytest.raises(OSError):
        get_free_port()
