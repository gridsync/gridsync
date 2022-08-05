from allmydata.uri import UnknownURI
from allmydata.uri import from_string as uri_from_string


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
        kind = cap.split(":")[1]
    except IndexError:
        return False
    return kind.endswith("-RO")


def diminish(cap: str) -> str:
    """
    Diminish a readwrite capability string into a read(only) one.

    If the capability is already a read(only) cap, return it unchanged.
    Raises a ValueError, if the capability type cannot be determined.
    """
    uri = uri_from_string(cap)
    if isinstance(uri, UnknownURI):
        raise ValueError(f'Unknown URI type: "{cap}"')
    return uri.get_readonly().to_string().decode("ascii")
