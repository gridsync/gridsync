import deterministic_keygen


def test_deterministic_rsa() -> None:
    phrase = deterministic_keygen.generate_phrase()
    key = deterministic_keygen.derive_rsa_key_from_phrase(phrase)
    assert key.startswith("-----BEGIN PRIVATE KEY-----")
