from allmydata.uri import UnknownURI
from allmydata.uri import from_string as uri_from_string


def diminish(cap: str) -> str:
    uri = uri_from_string(cap)
    if isinstance(uri, UnknownURI):
        raise ValueError(f'Unknown URI type: "{cap}"')
    return uri.get_readonly().to_string().decode("ascii")
