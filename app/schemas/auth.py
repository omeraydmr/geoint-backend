"""Authentication and user schemas"""
from pydantic import BaseModel, Field, EmailStr
from typing import Optional
from datetime import datetime
from uuid import UUID


# ============================================
# Authentication Schemas
# ============================================

class UserRegister(BaseModel):
    """User registration request"""
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=100)
    full_name: str = Field(..., min_length=1, max_length=255)


class UserLogin(BaseModel):
    """User login request"""
    email: EmailStr
    password: str


class Token(BaseModel):
    """JWT token response (legacy - use TokenResponse instead)"""
    access_token: str
    token_type: str = "bearer"


class TokenResponse(BaseModel):
    """Full token response with refresh token"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # Access token expiration in seconds


class RefreshTokenRequest(BaseModel):
    """Refresh token request"""
    refresh_token: str


class TokenData(BaseModel):
    """JWT token payload data"""
    user_id: Optional[str] = None


# ============================================
# User Schemas
# ============================================

class UserResponse(BaseModel):
    """User response"""
    id: UUID
    email: str
    full_name: Optional[str] = None
    is_active: bool
    is_superuser: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class UserUpdate(BaseModel):
    """User update request"""
    full_name: Optional[str] = Field(None, min_length=1, max_length=255)
    email: Optional[EmailStr] = None


class PasswordChange(BaseModel):
    """Password change request"""
    old_password: str
    new_password: str = Field(..., min_length=8, max_length=100)
