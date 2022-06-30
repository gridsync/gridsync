# -*- coding: utf-8 -*-
from unittest.mock import Mock

import pytest
from pytest_twisted import inlineCallbacks

from gridsync.tahoe import TahoeWebError
from gridsync.zkapauthorizer import PLUGIN_NAME, ZKAPAuthorizer


def fake_treq_request_resp_code_200(*args, **kwargs):
    fake_resp = Mock()
    fake_resp.code = 200
    fake_resp.content = Mock(return_value=b"")
    fake_request = Mock(return_value=fake_resp)
    return fake_request


def fake_treq_request_resp_code_500(*args, **kwargs):
    fake_resp = Mock()
    fake_resp.code = 500
    fake_request = Mock(return_value=fake_resp)
    return fake_request


@inlineCallbacks
def test__request_url(tahoe, monkeypatch):
    fake_request = fake_treq_request_resp_code_200()
    monkeypatch.setattr("treq.request", fake_request)
    monkeypatch.setattr("treq.content", lambda _: b"")
    yield ZKAPAuthorizer(tahoe)._request("GET", "/test")
    assert fake_request.call_args[0][1] == (
        tahoe.nodeurl + f"storage-plugins/{PLUGIN_NAME}/test"
    )


@inlineCallbacks
def test__request_headers(tahoe, monkeypatch):
    fake_request = fake_treq_request_resp_code_200()
    monkeypatch.setattr("treq.request", fake_request)
    monkeypatch.setattr("treq.content", lambda _: b"")
    yield ZKAPAuthorizer(tahoe)._request("GET", "/test")
    assert fake_request.call_args[1]["headers"] == {
        "Authorization": f"tahoe-lafs {tahoe.api_token}",
        "Content-Type": "application/json",
    }


@inlineCallbacks
def test_add_voucher_with_voucher(tahoe, monkeypatch):
    monkeypatch.setattr("treq.request", fake_treq_request_resp_code_200())
    monkeypatch.setattr("treq.content", lambda _: b"")
    result = yield ZKAPAuthorizer(tahoe).add_voucher("Test1234")
    assert result == "Test1234"


@inlineCallbacks
def test_add_voucher_without_voucher(tahoe, monkeypatch):
    monkeypatch.setattr("treq.request", fake_treq_request_resp_code_200())
    monkeypatch.setattr("treq.content", lambda _: b"")
    result = yield ZKAPAuthorizer(tahoe).add_voucher()
    assert len(result) == 44


@inlineCallbacks
def test_add_voucher_raise_tahoe_web_error(tahoe, monkeypatch):
    monkeypatch.setattr("treq.request", fake_treq_request_resp_code_500())
    monkeypatch.setattr("treq.content", lambda _: b"")
    with pytest.raises(TahoeWebError):
        yield ZKAPAuthorizer(tahoe).add_voucher()


@inlineCallbacks
def test_get_voucher(tahoe, monkeypatch):
    monkeypatch.setattr("treq.request", fake_treq_request_resp_code_200())
    monkeypatch.setattr("treq.content", lambda _: b'{"A": "A"}')
    result = yield ZKAPAuthorizer(tahoe).get_voucher("Test1234")
    assert result == {"A": "A"}


@inlineCallbacks
def test_get_voucher_raise_tahoe_web_error(tahoe, monkeypatch):
    monkeypatch.setattr("treq.request", fake_treq_request_resp_code_500())
    monkeypatch.setattr("treq.content", lambda _: b"")
    with pytest.raises(TahoeWebError):
        yield ZKAPAuthorizer(tahoe).get_voucher("Test1234")


@inlineCallbacks
def test_get_vouchers(tahoe, monkeypatch):
    monkeypatch.setattr("treq.request", fake_treq_request_resp_code_200())
    monkeypatch.setattr(
        "treq.content", lambda _: b'{"vouchers": [{"A": "A"}, {"B": "B"}]}'
    )
    result = yield ZKAPAuthorizer(tahoe).get_vouchers()
    assert result == [{"A": "A"}, {"B": "B"}]


@inlineCallbacks
def test_get_vouchers_raise_tahoe_web_error(tahoe, monkeypatch):
    monkeypatch.setattr("treq.request", fake_treq_request_resp_code_500())
    monkeypatch.setattr("treq.content", lambda _: b"")
    with pytest.raises(TahoeWebError):
        yield ZKAPAuthorizer(tahoe).get_vouchers()


@pytest.mark.parametrize(
    "zkap_payment_url_root,voucher,expected",
    [
        [
            "https://one.example.org/payment",
            "AAAAAAAA",
            "https://one.example.org/payment?voucher=AAAAAAAA&checksum="
            "c34ab6abb7b2bb595bc25c3b388c872fd1d575819a8f55cc689510285e212385",
        ],
        [
            "https://two.example.org/payment",
            "BBBBBBBB",
            "https://two.example.org/payment?voucher=BBBBBBBB&checksum="
            "2f858775d71cc4ece5f46f497c58c01167cd6fc301e56e935070f5e81bfe5890",
        ],
    ],
)
def test_zkap_payment_url(tahoe, zkap_payment_url_root, voucher, expected):
    zkapauthorizer = ZKAPAuthorizer(tahoe)
    zkapauthorizer.zkap_payment_url_root = zkap_payment_url_root
    url = zkapauthorizer.zkap_payment_url(voucher)
    assert url.endswith(expected) is True


def test_zkap_payment_url_empty_zkap_payment_root_url(tahoe):
    zkapauthorizer = ZKAPAuthorizer(tahoe)
    zkapauthorizer.zkap_payment_url_root = ""
    url = zkapauthorizer.zkap_payment_url("TestVoucher")
    assert url == ""


@inlineCallbacks
def test__get_content(tahoe, monkeypatch):
    monkeypatch.setattr("gridsync.tahoe.Tahoe.await_ready", Mock())
    monkeypatch.setattr("treq.get", fake_treq_request_resp_code_200())
    monkeypatch.setattr("treq.content", Mock(return_value=b"test"))
    result = yield ZKAPAuthorizer(tahoe)._get_content("URI:TEST")
    assert result == b"test"


@inlineCallbacks
def test__get_content_raise_tahoe_web_error(tahoe, monkeypatch):
    monkeypatch.setattr("gridsync.tahoe.Tahoe.await_ready", Mock())
    monkeypatch.setattr("treq.get", fake_treq_request_resp_code_500())
    monkeypatch.setattr("treq.content", Mock(return_value=b"test"))
    with pytest.raises(TahoeWebError):
        yield ZKAPAuthorizer(tahoe)._get_content("URI:TEST")


@inlineCallbacks
def test_get_version(tahoe, monkeypatch):
    monkeypatch.setattr("treq.request", fake_treq_request_resp_code_200())
    monkeypatch.setattr("treq.content", Mock(return_value=b'{"version": "9"}'))
    result = yield ZKAPAuthorizer(tahoe).get_version()
    assert result == "9"
