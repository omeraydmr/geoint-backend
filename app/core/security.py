"""Security utilities for authentication and authorization"""
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import uuid
import hashlib
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

from app.core.config import settings
from app.core.exceptions import RefreshTokenError, TokenExpiredError, TokenRevokedError


# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 scheme for token extraction
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password"""
    return pwd_context.hash(password)


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """
    Create JWT access token

    Args:
        data: Data to encode in the token (e.g., {"sub": user_id})
        expires_delta: Token expiration time

    Returns:
        Encoded JWT token
    """
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

    return encoded_jwt


def decode_access_token(token: str) -> Dict[str, Any]:
    """
    Decode and verify JWT token

    Args:
        token: JWT token to decode

    Returns:
        Decoded token payload

    Raises:
        HTTPException: If token is invalid or expired
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        return payload
    except JWTError:
        raise credentials_exception


async def get_current_user(
    token: str = Depends(oauth2_scheme),
) -> Dict[str, Any]:
    """
    Get current authenticated user from JWT token

    Args:
        token: JWT bearer token

    Returns:
        User data from token payload

    Raises:
        HTTPException: If token is invalid
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
        return {"id": user_id, **payload}
    except JWTError:
        raise credentials_exception


async def get_current_active_user(
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Get current active user (checks if user is not disabled)

    Args:
        current_user: Current user from get_current_user dependency

    Returns:
        Active user

    Raises:
        HTTPException: If user is inactive/disabled
    """
    is_active = current_user.get('is_active', True)

    if not is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    return current_user


# ================================================================================
# Refresh Token Functions
# ================================================================================

def create_refresh_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """
    Create JWT refresh token with longer expiration.

    Args:
        data: Data to encode (should include {"sub": user_id})
        expires_delta: Token expiration time (default: 7 days)

    Returns:
        Encoded JWT refresh token
    """
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

    # Add unique token ID (jti) for token tracking/revocation
    to_encode.update({
        "exp": expire,
        "jti": str(uuid.uuid4()),
        "type": "refresh"
    })

    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return encoded_jwt


def decode_refresh_token(token: str) -> Dict[str, Any]:
    """
    Decode and verify refresh token.

    Args:
        token: JWT refresh token to decode

    Returns:
        Decoded token payload

    Raises:
        RefreshTokenError: If token is invalid
        TokenExpiredError: If token has expired
    """
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])

        # Verify it's a refresh token
        if payload.get("type") != "refresh":
            raise RefreshTokenError("Invalid token type")

        return payload

    except jwt.ExpiredSignatureError:
        raise TokenExpiredError("Refresh token has expired", token_type="refresh")
    except JWTError as e:
        raise RefreshTokenError(f"Invalid refresh token: {str(e)}")


def hash_token(token: str) -> str:
    """
    Hash a token for secure storage in database.

    Args:
        token: Plain token string

    Returns:
        Hashed token (SHA-256)
    """
    return hashlib.sha256(token.encode()).hexdigest()


async def store_refresh_token(
    db: AsyncSession,
    user_id: str,
    token: str,
    expires_at: datetime,
    device_info: Optional[str] = None,
    ip_address: Optional[str] = None,
) -> None:
    """
    Store refresh token in database (hashed).

    Args:
        db: Database session
        user_id: User ID
        token: Refresh token (will be hashed)
        expires_at: Token expiration time
        device_info: User agent / device information
        ip_address: Client IP address
    """
    from app.models.refresh_token import RefreshToken

    # Hash the token before storage
    hashed_token = hash_token(token)

    # Check token limit per user and cleanup old tokens if needed
    result = await db.execute(
        select(RefreshToken)
        .where(RefreshToken.user_id == user_id)
        .order_by(RefreshToken.created_at.desc())
    )
    existing_tokens = result.scalars().all()

    # If user has max tokens, delete oldest ones
    if len(existing_tokens) >= settings.MAX_REFRESH_TOKENS_PER_USER:
        tokens_to_delete = existing_tokens[settings.MAX_REFRESH_TOKENS_PER_USER - 1:]
        for old_token in tokens_to_delete:
            await db.delete(old_token)

    # Create new refresh token record
    refresh_token = RefreshToken(
        user_id=uuid.UUID(user_id),
        token=hashed_token,
        expires_at=expires_at,
        device_info=device_info,
        ip_address=ip_address,
    )

    db.add(refresh_token)
    await db.commit()


async def verify_refresh_token(db: AsyncSession, token: str) -> Dict[str, Any]:
    """
    Verify refresh token exists in database and is valid.

    Args:
        db: Database session
        token: Refresh token to verify

    Returns:
        Token payload

    Raises:
        RefreshTokenError: If token is invalid
        TokenExpiredError: If token has expired
        TokenRevokedError: If token has been revoked
    """
    from app.models.refresh_token import RefreshToken

    # Decode token first
    payload = decode_refresh_token(token)

    # Hash token for database lookup
    hashed_token = hash_token(token)

    # Find token in database
    result = await db.execute(
        select(RefreshToken).where(RefreshToken.token == hashed_token)
    )
    db_token = result.scalar_one_or_none()

    if not db_token:
        raise RefreshTokenError("Refresh token not found in database")

    # Check if revoked
    if db_token.is_revoked:
        raise TokenRevokedError("Refresh token has been revoked")

    # Check if expired
    if db_token.is_expired:
        raise TokenExpiredError("Refresh token has expired", token_type="refresh")

    return payload


async def revoke_refresh_token(db: AsyncSession, token: str) -> None:
    """
    Revoke a specific refresh token (logout from single device).

    Args:
        db: Database session
        token: Refresh token to revoke
    """
    from app.models.refresh_token import RefreshToken

    hashed_token = hash_token(token)

    result = await db.execute(
        select(RefreshToken).where(RefreshToken.token == hashed_token)
    )
    db_token = result.scalar_one_or_none()

    if db_token:
        db_token.revoked_at = datetime.utcnow()
        await db.commit()


async def revoke_all_user_tokens(db: AsyncSession, user_id: str) -> int:
    """
    Revoke all refresh tokens for a user (logout from all devices).

    Args:
        db: Database session
        user_id: User ID

    Returns:
        Number of tokens revoked
    """
    from app.models.refresh_token import RefreshToken

    result = await db.execute(
        select(RefreshToken).where(
            RefreshToken.user_id == uuid.UUID(user_id),
            RefreshToken.revoked_at.is_(None)
        )
    )
    tokens = result.scalars().all()

    for token in tokens:
        token.revoked_at = datetime.utcnow()

    await db.commit()
    return len(tokens)


async def cleanup_expired_tokens(db: AsyncSession) -> int:
    """
    Delete expired refresh tokens from database.
    Should be run periodically (e.g., daily cron job).

    Args:
        db: Database session

    Returns:
        Number of tokens deleted
    """
    from app.models.refresh_token import RefreshToken

    result = await db.execute(
        delete(RefreshToken).where(RefreshToken.expires_at < datetime.utcnow())
    )
    await db.commit()

    return result.rowcount
