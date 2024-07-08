from tahoe_capabilities import (
    NotRecognized,
    capability_from_string,
    danger_real_capability_string,
    is_read,
    is_verify,
    is_write,
)


def is_readonly(cap: str) -> bool:
    """
    Determine whether a given capability string is a readonly cap.

    The "only" part in "readonly" is the important qualifier here; a
    "readonly cap" here refers to a capability with which the
    corresponding data can be read but nothing else. This *excludes*
    both write-capabilities and verify-capabilities (even though
    verify-caps can be derived from read(only)-caps).

    This function is needed because tahoe's `IURI.is_readonly` returns
    `True` for verify-capabilities (even though the purpose of verify-
    caps is to *prevent* reading).

    """
    try:
        c = capability_from_string(cap)
    except NotRecognized:
        return False
    return is_read(c) and not is_write(c) and not is_verify(c)


def diminish(cap: str) -> str:
    """
    Diminish a readwrite capability string into a read(only) one.

    If the capability is already a read(only) cap, return it unchanged.
    Raises a ValueError, if the capability type cannot be determined.
    """
    try:
        c = capability_from_string(cap)
    except (NotRecognized, KeyError) as e:
        raise ValueError(f'Unknown URI type: "{cap}"') from e
    if is_read(c) and not is_write(c) and not is_verify(c):
        return cap
    # FIXME mypy warns 'Item [...] has no attribute "reader"'
    return danger_real_capability_string(c.reader)  # type: ignore


def derive_mutable_cap(rsa_key_pem: str, kind: str = "DIR2") -> str:
    """
    Derive a mutable capability string from a given RSA private key.
    """
    from base64 import b32encode

    from allmydata.util.hashutil import (
        ssk_pubkey_fingerprint_hash,
        ssk_writekey_hash,
    )
    from cryptography.hazmat.primitives import serialization

    priv_key = serialization.load_pem_private_key(
        rsa_key_pem.encode(),
        password=None,
    )
    priv_key_der = priv_key.private_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )

    pub_key = priv_key.public_key()
    pub_key_der = pub_key.public_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )

    writekey_hash = ssk_writekey_hash(priv_key_der)
    fingerprint_hash = ssk_pubkey_fingerprint_hash(pub_key_der)

    writekey = b32encode(writekey_hash).decode().rstrip("=").lower()
    fingerprint = b32encode(fingerprint_hash).decode().rstrip("=").lower()

    return f"URI:{kind}:{writekey}:{fingerprint}"
