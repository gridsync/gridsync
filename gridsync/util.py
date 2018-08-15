# -*- coding: utf-8 -*-

from binascii import hexlify, unhexlify


B58_ALPHABET = '123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz'


def b58encode(b):  # Adapted from python-bitcoinlib
    n = int('0x0' + hexlify(b).decode('utf8'), 16)
    res = []
    while n:
        n, r = divmod(n, 58)
        res.append(B58_ALPHABET[r])
    res = ''.join(res[::-1])
    pad = 0
    for c in b:
        if c == 0:
            pad += 1
        else:
            break
    return B58_ALPHABET[0] * pad + res


def b58decode(s):  # Adapted from python-bitcoinlib
    if not s:
        return b''
    n = 0
    for c in s:
        n *= 58
        if c not in B58_ALPHABET:
            raise ValueError(
                "Character '%r' is not a valid base58 character" % c)
        digit = B58_ALPHABET.index(c)
        n += digit
    h = '%x' % n
    if len(h) % 2:
        h = '0' + h
    res = unhexlify(h.encode('utf8'))
    pad = 0
    for c in s[:-1]:
        if c == B58_ALPHABET[0]:
            pad += 1
        else:
            break
    return b'\x00' * pad + res


def humanized_list(list_, kind='files'):
    if not list_:
        return None
    if len(list_) == 1:
        return list_[0]
    if len(list_) == 2:
        return " and ".join(list_)
    if len(list_) == 3:
        return "{}, {}, and {}".format(*list_)
    return "{}, {}, and {} other {}".format(list_[0], list_[1],
                                            len(list_) - 2, kind)
