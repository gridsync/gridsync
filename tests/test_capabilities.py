import pytest

from gridsync.capabilities import diminish, is_readonly


@pytest.mark.parametrize(
    "cap, result",
    [
        (
            "URI:DIR2:h6esoa5ca2bkwgersspqfk5gty:ixphgtnlhm3eypfcbadnh3ywzrthua4vxgldywh6nbq2ligddl3q",
            False,
        ),
        (
            "URI:DIR2-RO:cq4zshembnmo4bcaroimldwv4e:ixphgtnlhm3eypfcbadnh3ywzrthua4vxgldywh6nbq2ligddl3q",
            True,
        ),
        (
            "URI:DIR2-Verifier:l2fvhyj6kvgxbmkkoslwbsspca:ixphgtnlhm3eypfcbadnh3ywzrthua4vxgldywh6nbq2ligddl3q",
            False,
        ),
        ("", False),
        (
            "URI:CHK:5qm4v3trdsrir2q3ojjpjk2qgi:wkf3l4kziur5vwipywwfjaerxo6e62oazjeejazy7cfgiaghizsa:1:1:1024",
            False,
        ),
        (
            "URI:CHK-Verifier:3gskkineg6sibcgryovfcv7k3q:wkf3l4kziur5vwipywwfjaerxo6e62oazjeejazy7cfgiaghizsa:1:1:1024",
            False,
        ),
        ("URI:LIT:orsxg5ak", False),
        (
            "URI:DIR2-MDMF:hlnh33k7kuk2lv3u46cc6ipe3e:bt2ck3zo7qyaje7hpgnpsec3vkfb73dyedeihlv3z4ayuo5vsb5q",
            False,
        ),
        (
            "URI:DIR2-MDMF-RO:26ffbgqpboxqbnlji7aiuhhs2y:bt2ck3zo7qyaje7hpgnpsec3vkfb73dyedeihlv3z4ayuo5vsb5q",
            True,
        ),
        (
            "URI:DIR2-MDMF-Verifier:dit7a7nmrpo4gxajzeftlblkdu:bt2ck3zo7qyaje7hpgnpsec3vkfb73dyedeihlv3z4ayuo5vsb5q",
            False,
        ),
        (
            "URI:MDMF:2qgrugxjwdmuoycbvdseyq2raa:puuqfsh7fnqedjrpj7qz6letucxbuazarn3mwcz7wozs7e52hutq",
            False,
        ),
        (
            "URI:MDMF-RO:lgoqqoaxlbz7klyzuoq6wn2zm4:puuqfsh7fnqedjrpj7qz6letucxbuazarn3mwcz7wozs7e52hutq",
            True,
        ),
        (
            "URI:MDMF-Verifier:f33zj4ddzz7dpa6czuyqxhoqua:puuqfsh7fnqedjrpj7qz6letucxbuazarn3mwcz7wozs7e52hutq",
            False,
        ),
        (
            "URI:DIR2:n327fuwvobl2wkf54trr3d5kqe:ecvkvj6wxgdzqevqgtks3h25asudikqzl6smehq5gtdf22pls2wa",
            False,
        ),
        (
            "URI:DIR2-RO:rvukfg5e4hqnpd4pgmwbna3rjy:ecvkvj6wxgdzqevqgtks3h25asudikqzl6smehq5gtdf22pls2wa",
            True,
        ),
        (
            "URI:DIR2-Verifier:wad5f2t5q4gaed6oxbhirgqrlq:ecvkvj6wxgdzqevqgtks3h25asudikqzl6smehq5gtdf22pls2wa",
            False,
        ),
        (
            "URI:SSK:5gmdbkkqgnc2fm2zmrlbcia5tm:mqwoiegvel4vl7qn5ln27qxpel7z3owe73lagvv4xwx3pxndintq",
            False,
        ),
        (
            "URI:SSK-RO:wrcjmvntgvvb5s4xldlcepnu7u:mqwoiegvel4vl7qn5ln27qxpel7z3owe73lagvv4xwx3pxndintq",
            True,
        ),
        (
            "URI:SSK-Verifier:dsjz5zc7sewwzdnkp6dg2plp4i:mqwoiegvel4vl7qn5ln27qxpel7z3owe73lagvv4xwx3pxndintq",
            False,
        ),
    ],
)
def test_is_readonly(cap, result):
    assert is_readonly(cap) == result


@pytest.mark.parametrize(
    "rw_uri, ro_uri",
    [
        (
            "URI:DIR2:h6esoa5ca2bkwgersspqfk5gty:ixphgtnlhm3eypfcbadnh3ywzrthua4vxgldywh6nbq2ligddl3q",
            "URI:DIR2-RO:cq4zshembnmo4bcaroimldwv4e:ixphgtnlhm3eypfcbadnh3ywzrthua4vxgldywh6nbq2ligddl3q",
        ),
        (
            "URI:DIR2-MDMF:hlnh33k7kuk2lv3u46cc6ipe3e:bt2ck3zo7qyaje7hpgnpsec3vkfb73dyedeihlv3z4ayuo5vsb5q",
            "URI:DIR2-MDMF-RO:26ffbgqpboxqbnlji7aiuhhs2y:bt2ck3zo7qyaje7hpgnpsec3vkfb73dyedeihlv3z4ayuo5vsb5q",
        ),
        (
            "URI:MDMF:2qgrugxjwdmuoycbvdseyq2raa:puuqfsh7fnqedjrpj7qz6letucxbuazarn3mwcz7wozs7e52hutq",
            "URI:MDMF-RO:lgoqqoaxlbz7klyzuoq6wn2zm4:puuqfsh7fnqedjrpj7qz6letucxbuazarn3mwcz7wozs7e52hutq",
        ),
        (
            "URI:DIR2:n327fuwvobl2wkf54trr3d5kqe:ecvkvj6wxgdzqevqgtks3h25asudikqzl6smehq5gtdf22pls2wa",
            "URI:DIR2-RO:rvukfg5e4hqnpd4pgmwbna3rjy:ecvkvj6wxgdzqevqgtks3h25asudikqzl6smehq5gtdf22pls2wa",
        ),
        (
            "URI:SSK:5gmdbkkqgnc2fm2zmrlbcia5tm:mqwoiegvel4vl7qn5ln27qxpel7z3owe73lagvv4xwx3pxndintq",
            "URI:SSK-RO:wrcjmvntgvvb5s4xldlcepnu7u:mqwoiegvel4vl7qn5ln27qxpel7z3owe73lagvv4xwx3pxndintq",
        ),
    ],
)
def test_diminish_converts_rw_to_ro(rw_uri, ro_uri):
    assert diminish(rw_uri) == ro_uri


def test_diminish_raises_value_error_if_uri_type_is_unknown():
    with pytest.raises(ValueError):
        assert diminish("URI:UNKNOWN:aaaaaaaa:bbbbbbbb")


def test_diminish_returns_cap_if_cap_is_already_readonly():
    cap = "URI:DIR2-RO:cq4zshembnmo4bcaroimldwv4e:ixphgtnlhm3eypfcbadnh3ywzrthua4vxgldywh6nbq2ligddl3q"
    assert diminish(cap) == cap
