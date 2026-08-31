import pytest

from florabase.auth.security import (
    TOKEN_BYTES,
    new_token,
    normalize_login_name,
    password_hasher,
    token_digest,
    validate_password,
)


def test_login_name_normalization_is_bounded_ascii() -> None:
    assert normalize_login_name("  OWNER.Name_1 ") == "owner.name_1"

    for invalid in ("ab", "owner name", "öwner", "owner/one", "x" * 65):
        with pytest.raises(ValueError, match="Login name"):
            normalize_login_name(invalid)


def test_password_policy_bounds_work_factor_input() -> None:
    assert validate_password("correct horse battery staple") == "correct horse battery staple"
    with pytest.raises(ValueError, match="Password"):
        validate_password("too-short")
    with pytest.raises(ValueError, match="Password"):
        validate_password("x" * 1_025)


def test_argon2id_and_random_token_primitives() -> None:
    encoded = password_hasher().hash("correct horse battery staple")
    first = new_token()
    second = new_token()

    assert encoded.startswith("$argon2id$v=19$m=65536,t=3,p=1$")
    assert password_hasher().verify("correct horse battery staple", encoded)
    assert first != second
    assert len(token_digest(first)) == TOKEN_BYTES
    assert token_digest(first) != token_digest(second)
