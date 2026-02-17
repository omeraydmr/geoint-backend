"""
Authentication API Endpoints

Provides endpoints for:
- User registration
- User login (JWT tokens)
- Token refresh
- User profile management
- Password change
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request, Body
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Any
import logging
from datetime import datetime, timedelta

from app.core.database import get_db
from app.core.security import (
    get_password_hash,
    verify_password,
    create_access_token,
    create_refresh_token,
    verify_refresh_token,
    store_refresh_token,
    revoke_refresh_token,
    revoke_all_user_tokens,
    get_current_active_user,
)
from app.core.config import settings
from app.models.user import User
from typing import Dict
from app.schemas.auth import (
    UserRegister,
    UserLogin,
    Token,
    TokenResponse,
    RefreshTokenRequest,
    UserResponse,
    UserUpdate,
    PasswordChange,
)

logger = logging.getLogger(__name__)
router = APIRouter()


# ============================================
# Authentication Endpoints
# ============================================

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserRegister,
    db: AsyncSession = Depends(get_db)
):
    """
    Register a new user

    Creates a new user account with hashed password.
    """
    try:
        # Check if user already exists
        result = await db.execute(
            select(User).where(User.email == user_data.email)
        )
        existing_user = result.scalar_one_or_none()

        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )

        # Create user
        user = User(
            email=user_data.email,
            hashed_password=get_password_hash(user_data.password),
            full_name=user_data.full_name,
            is_active=True,
            is_superuser=False,
        )

        db.add(user)
        await db.commit()
        await db.refresh(user)

        logger.info(f"✅ Registered new user: {user.email}")
        return UserResponse.model_validate(user)

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"❌ Error registering user: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to register user"
        )


@router.post("/login", response_model=TokenResponse)
async def login(
    user_data: UserLogin,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Login with email and password

    Returns JWT access token and refresh token.
    """
    try:
        # Get user
        result = await db.execute(
            select(User).where(User.email == user_data.email)
        )
        user = result.scalar_one_or_none()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Verify password
        if not verify_password(user_data.password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Check if user is active
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Inactive user"
            )

        # Create access token
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": str(user.id)},
            expires_delta=access_token_expires
        )

        # Create refresh token
        refresh_token_expires = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        refresh_token = create_refresh_token(
            data={"sub": str(user.id)},
            expires_delta=refresh_token_expires
        )

        # Store refresh token in database
        device_info = request.headers.get("user-agent", "Unknown")
        ip_address = request.client.host if request.client else None

        await store_refresh_token(
            db=db,
            user_id=str(user.id),
            token=refresh_token,
            expires_at=datetime.utcnow() + refresh_token_expires,
            device_info=device_info,
            ip_address=ip_address,
        )

        # Update last login
        user.last_login_at = datetime.utcnow()
        await db.commit()

        logger.info(f"User logged in: {user.email}")
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error during login: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed"
        )


@router.post("/token", response_model=Token)
async def login_oauth(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db)
):
    """
    OAuth2 compatible token endpoint

    Used by frontend OAuth2 clients.
    Username field should contain the email address.
    """
    try:
        # Get user
        result = await db.execute(
            select(User).where(User.email == form_data.username)
        )
        user = result.scalar_one_or_none()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Verify password
        if not verify_password(form_data.password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Check if user is active
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Inactive user"
            )

        # Create access token
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": str(user.id)},
            expires_delta=access_token_expires
        )

        return Token(access_token=access_token, token_type="bearer")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error during OAuth login: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed"
        )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_access_token(
    request: Request,
    refresh_data: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Refresh access token using refresh token.

    Returns new access token and refresh token (token rotation).
    """
    try:
        # Verify refresh token
        payload = await verify_refresh_token(db, refresh_data.refresh_token)
        user_id = payload.get("sub")

        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token"
            )

        # Get user from database
        result = await db.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found"
            )

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Inactive user"
            )

        # Create new access token
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": str(user.id)},
            expires_delta=access_token_expires
        )

        # Create new refresh token (token rotation for security)
        refresh_token_expires = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        new_refresh_token = create_refresh_token(
            data={"sub": str(user.id)},
            expires_delta=refresh_token_expires
        )

        # Revoke old refresh token
        await revoke_refresh_token(db, refresh_data.refresh_token)

        # Store new refresh token
        device_info = request.headers.get("user-agent", "Unknown")
        ip_address = request.client.host if request.client else None

        await store_refresh_token(
            db=db,
            user_id=str(user.id),
            token=new_refresh_token,
            expires_at=datetime.utcnow() + refresh_token_expires,
            device_info=device_info,
            ip_address=ip_address,
        )

        logger.info(f"Token refreshed for user: {user.email}")
        return TokenResponse(
            access_token=access_token,
            refresh_token=new_refresh_token,
            token_type="bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error refreshing token: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not refresh token"
        )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    refresh_token: str = Body(..., embed=True),
    db: AsyncSession = Depends(get_db)
):
    """
    Logout from current device.

    Revokes the provided refresh token.
    """
    try:
        await revoke_refresh_token(db, refresh_token)
        logger.info("User logged out from device")
        return None

    except Exception as e:
        logger.error(f"Error during logout: {e}")
        # Don't fail logout even if token not found
        return None


@router.post("/logout-all", status_code=status.HTTP_204_NO_CONTENT)
async def logout_all_devices(
    current_user: Dict = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Logout from all devices.

    Revokes all refresh tokens for the current user.
    """
    try:
        user_id = current_user.get("id")
        count = await revoke_all_user_tokens(db, user_id)
        logger.info(f"User logged out from all devices ({count} tokens revoked)")
        return None

    except Exception as e:
        logger.error(f"Error during logout all: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Logout failed"
        )


# ============================================
# User Profile Endpoints
# ============================================

@router.get("/me", response_model=UserResponse)
async def get_current_user_profile(
    current_user: Dict = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get current user profile

    Requires valid JWT token.
    """
    logger.debug(f"📥 GET /auth/me - user_id: {current_user.get('id')}")
    # Fetch full user from database
    result = await db.execute(
        select(User).where(User.id == current_user.get("id"))
    )
    user = result.scalar_one_or_none()
    if not user:
        logger.warning(f"⚠️ User not found: {current_user.get('id')}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    logger.debug(f"📤 GET /auth/me - returning user: {user.email}")
    return UserResponse.model_validate(user)


@router.patch("/me", response_model=UserResponse)
async def update_current_user_profile(
    user_data: UserUpdate,
    current_user: Dict = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update current user profile
    """
    try:
        # Fetch full user from database
        result = await db.execute(
            select(User).where(User.id == current_user.get("id"))
        )
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        # If email is being changed, check if it's already taken
        if user_data.email and user_data.email != user.email:
            result = await db.execute(
                select(User).where(User.email == user_data.email)
            )
            existing_user = result.scalar_one_or_none()

            if existing_user:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Email already registered"
                )

        # Update fields
        update_data = user_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(user, field, value)

        user.updated_at = datetime.utcnow()

        await db.commit()
        await db.refresh(user)

        logger.info(f"✅ Updated user profile: {user.email}")
        return UserResponse.model_validate(user)

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"❌ Error updating user profile: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update profile"
        )


@router.post("/me/change-password", status_code=status.HTTP_200_OK)
async def change_password(
    password_data: PasswordChange,
    current_user: Dict = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Change current user password
    """
    try:
        # Fetch full user from database
        result = await db.execute(
            select(User).where(User.id == current_user.get("id"))
        )
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        # Verify old password
        if not verify_password(password_data.old_password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Incorrect password"
            )

        # Update password
        user.hashed_password = get_password_hash(password_data.new_password)
        user.updated_at = datetime.utcnow()

        await db.commit()

        logger.info(f"✅ Changed password for user: {user.email}")
        return {"message": "Password changed successfully"}

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"❌ Error changing password: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to change password"
        )


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
async def delete_current_user(
    current_user: Dict = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete current user account

    WARNING: This action is irreversible and will delete all associated data.
    """
    try:
        # Fetch full user from database
        result = await db.execute(
            select(User).where(User.id == current_user.get("id"))
        )
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        await db.delete(user)
        await db.commit()

        logger.info(f"✅ Deleted user account: {user.email}")

    except Exception as e:
        await db.rollback()
        logger.error(f"❌ Error deleting user: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete user"
        )
