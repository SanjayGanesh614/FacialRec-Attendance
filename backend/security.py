# app/core/security.py
# ─────────────────────────────────────────────────────────────
# All cryptographic operations live here.
# Nothing else should import jose or passlib directly.
# ─────────────────────────────────────────────────────────────

from datetime import datetime, timedelta, timezone
from typing import Optional, Literal
from uuid import UUID

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

# bcrypt is the gold standard for password hashing.
# deprecated="auto" means passlib will upgrade old hashes on next login.
_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ── Password hashing ───────────────────────────────────────────────────────────

def hash_password(plain: str) -> str:
    """Hash a plain-text password. Store the result, never the plain text."""
    return _pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    """Return True if plain matches the stored bcrypt hash."""
    return _pwd_context.verify(plain, hashed)


# ── JWT ───────────────────────────────────────────────────────────────────────

def _make_token(
    subject: str,                         # usually employee UUID as string
    token_type: Literal["access", "refresh"],
    expires_delta: timedelta,
    extra_claims: Optional[dict] = None,
) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": subject,
        "type": token_type,
        "iat": now,
        "exp": now + expires_delta,
    }
    if extra_claims:
        payload.update(extra_claims)
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_access_token(employee_id: UUID, role: str) -> str:
    """
    Short-lived token attached to every API request.
    Contains role so we don't hit DB on every request.
    """
    return _make_token(
        subject=str(employee_id),
        token_type="access",
        expires_delta=timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES),
        extra_claims={"role": role},
    )


def create_refresh_token(employee_id: UUID) -> str:
    """
    Long-lived token used only at /auth/refresh to get a new access token.
    Does NOT contain role — role is always re-read from DB on refresh.
    """
    return _make_token(
        subject=str(employee_id),
        token_type="refresh",
        expires_delta=timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS),
    )


def decode_token(token: str) -> dict:
    """
    Decode and validate a JWT.

    Raises JWTError (from python-jose) if:
      - signature is invalid
      - token has expired
      - token is malformed

    Callers should catch JWTError and raise HTTP 401.
    """
    return jwt.decode(
        token,
        settings.JWT_SECRET_KEY,
        algorithms=[settings.JWT_ALGORITHM],
    )


def verify_access_token(token: str) -> Optional[dict]:
    """
    Verify an access token specifically.
    Returns the payload dict, or None if invalid.
    Checks token type so refresh tokens can't be used as access tokens.
    """
    try:
        payload = decode_token(token)
        if payload.get("type") != "access":
            return None
        return payload
    except JWTError:
        return None


def verify_refresh_token(token: str) -> Optional[str]:
    """
    Verify a refresh token and return the subject (employee_id string).
    Returns None if invalid.
    """
    try:
        payload = decode_token(token)
        if payload.get("type") != "refresh":
            return None
        return payload.get("sub")
    except JWTError:
        return None
