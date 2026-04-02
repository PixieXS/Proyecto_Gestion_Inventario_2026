import base64
import hashlib
import hmac
import secrets


PBKDF2_PREFIX = "pbkdf2_sha256"
PBKDF2_ITERATIONS = 260000


def legacy_hash_password(password: str) -> str:
    """Compatibilidad con hashes antiguos SHA-256 sin sal."""
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def hash_password(password: str, *, salt: bytes | None = None,
                  iterations: int = PBKDF2_ITERATIONS) -> str:
    """Genera un hash PBKDF2 seguro y autocontenido."""
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        iterations,
    )
    salt_b64 = base64.b64encode(salt).decode("ascii")
    digest_b64 = base64.b64encode(digest).decode("ascii")
    return f"{PBKDF2_PREFIX}${iterations}${salt_b64}${digest_b64}"


def needs_rehash(stored_hash: str | None) -> bool:
    return not (stored_hash or "").startswith(f"{PBKDF2_PREFIX}$")


def verify_password(password: str, stored_hash: str | None) -> bool:
    if not stored_hash:
        return False

    if needs_rehash(stored_hash):
        expected = legacy_hash_password(password)
        return hmac.compare_digest(expected, stored_hash)

    try:
        _prefix, iterations_raw, salt_b64, digest_b64 = stored_hash.split("$", 3)
        iterations = int(iterations_raw)
        salt = base64.b64decode(salt_b64.encode("ascii"))
        expected = base64.b64decode(digest_b64.encode("ascii"))
    except Exception:
        return False

    candidate = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        iterations,
    )
    return hmac.compare_digest(candidate, expected)
