from allmydata import uri


def diminish(cap: str) -> str:
    return uri.from_string(cap).get_readonly().to_string().decode("ascii")
