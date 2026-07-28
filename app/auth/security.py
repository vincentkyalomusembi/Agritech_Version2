"""
Security utilities for authentication.

This module is responsible for:

1. Hashing farmer PINs before storing them.
2. Verifying entered PINs during login.
3. Creating JWT access tokens.
4. Decoding and validating JWT access tokens.

"""

from datetime import datetime, timedelta, timezone
from typing import Any

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings



# Password Hashing Configuration


# CryptContext manages password hashing.
# We use bcrypt because it is secure and recommended for storing passwords
# and PINs.
#
# Example:
#
# PIN:
#     1234
#
# Stored in database:
#     $2b$12$7L6....
#
# The original PIN can never be recovered from the hash.
#
pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
)



# JWT Configuration

#The algorithm used to sign the JWT tokens. HS256 is a symmetric algorithm that uses a secret key.

ALGORITHM = "HS256"

# Token expiration time in minutes.
# ---- Copilot Improvement ----
# Keep token lifetime configurable while preserving the existing 30-minute
# default; issuer/audience claims prevent tokens from other services being used.
# ---- End Improvement ----
ACCESS_TOKEN_EXPIRE_MINUTES = settings.ACCESS_TOKEN_EXPIRE_MINUTES



# Hash a PIN

def hash_pin(pin: str) -> str:
    """
    Hash a farmer PIN before saving it to the database.

    Parameters
    ----------
    pin : str
        The plain text PIN entered by the farmer.

    Returns
    -------
    str
        A secure bcrypt hash.
    """

    return pwd_context.hash(pin)



# Verify a PIN

def verify_pin(plain_pin: str, hashed_pin: str) -> bool:
    """
    Verify an entered PIN against the stored hash.

    Parameters
    ----------
    plain_pin : str
        PIN entered during login.

    hashed_pin : str
        PIN hash stored in the database.

    Returns
    -------
    bool
        True if the PIN is correct.
        False otherwise.
    """

    return pwd_context.verify(plain_pin, hashed_pin)



# Create JWT Access Token

def create_access_token(
    data: dict[str, Any],
    expires_delta: timedelta | None = None,
) -> str:
    """
    Create a signed JWT access token.

    Parameters
    ----------
    data : dict
        Data to store inside the token.

    expires_delta : timedelta | None
        Optional custom expiration time.

    Returns
    -------
    str
        Encoded JWT token.
    """

    # Create a copy so the original dictionary is not modified.
    to_encode = data.copy()

    # Determine token expiration.
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=ACCESS_TOKEN_EXPIRE_MINUTES
        )

    # ---- Copilot Improvement ----
    # Require a configured signing key and include standard validation claims.
    # Empty keys must never silently sign production JWTs.
    # ---- End Improvement ----
    if not settings.SECRET_KEY:
        raise RuntimeError("JWT signing is not configured.")

    now = datetime.now(timezone.utc)
    to_encode.update({
        "exp": expire,
        "iat": now,
        "iss": settings.JWT_ISSUER,
        "aud": settings.JWT_AUDIENCE,
    })

    # Encode and sign the token.
    encoded_jwt = jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=ALGORITHM,
    )

    return encoded_jwt



# Decode JWT Access Token

def decode_access_token(token: str) -> dict[str, Any]:
    """
    Decode and validate a JWT access token.

    Parameters
    ----------
    token : str
        JWT token received from the client.

    Returns
    -------
    dict
        Decoded payload.

    Raises
    ------
    JWTError
        If the token is invalid or has expired.
    """

    # ---- Copilot Improvement ----
    # Validate issuer and audience in addition to signature and expiry.
    # ---- End Improvement ----
    if not settings.SECRET_KEY:
        raise JWTError("JWT signing is not configured.")

    payload = jwt.decode(
        token,
        settings.SECRET_KEY,
        algorithms=[ALGORITHM],
        issuer=settings.JWT_ISSUER,
        audience=settings.JWT_AUDIENCE,
    )

    return payload
