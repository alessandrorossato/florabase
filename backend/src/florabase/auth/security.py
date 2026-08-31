import hashlib
import re
import secrets
from functools import lru_cache

from pwdlib import PasswordHash
from pwdlib.hashers.argon2 import Argon2Hasher

ARGON2_MEMORY_COST_KIB = 65_536
ARGON2_TIME_COST = 3
ARGON2_PARALLELISM = 1
TOKEN_BYTES = 32
LOGIN_NAME_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._-]{2,63}$")


@lru_cache
def password_hasher() -> PasswordHash:
    return PasswordHash(
        (
            Argon2Hasher(
                memory_cost=ARGON2_MEMORY_COST_KIB,
                time_cost=ARGON2_TIME_COST,
                parallelism=ARGON2_PARALLELISM,
            ),
        )
    )


@lru_cache
def dummy_password_hash() -> str:
    return password_hasher().hash(secrets.token_urlsafe(TOKEN_BYTES))


def normalize_login_name(login_name: str) -> str:
    normalized = login_name.strip().lower()
    if not LOGIN_NAME_PATTERN.fullmatch(normalized):
        raise ValueError(
            "Login name must be 3-64 lowercase ASCII letters, digits, dots, underscores, or hyphens"
        )
    return normalized


def validate_password(password: str) -> str:
    if len(password) < 12 or len(password) > 1_024:
        raise ValueError("Password must be between 12 and 1024 characters")
    return password


def new_token() -> str:
    return secrets.token_urlsafe(TOKEN_BYTES)


def token_digest(token: str) -> bytes:
    return hashlib.sha256(token.encode("ascii")).digest()
