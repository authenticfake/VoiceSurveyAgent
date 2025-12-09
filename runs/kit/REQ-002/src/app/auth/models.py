"""Authentication data models and DTOs."""
import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field

from app.shared.models.enums import UserRole

class TokenPayload(BaseModel):
    """JWT token payload structure."""
    
    sub: str = Field(..., description="OIDC subject identifier")
    exp: datetime = Field(..., description="Token expiration time")
    iat: datetime = Field(..., description="Token issued at time")
    iss: str = Field(..., description="Token issuer")
    aud: str | list[str] = Field(..., description="Token audience")
    email: Optional[str] = Field(None, description="User email from claims")
    name: Optional[str] = Field(None, description="User display name")
    roles: list[str] = Field(default_factory=list, description="User roles")
    
    class Config:
        """Pydantic configuration."""
        
        json_encoders = {
            datetime: lambda v: v.isoformat(),
        }

class UserInfo(BaseModel):
    """User information from OIDC userinfo endpoint."""
    
    sub: str = Field(..., description="OIDC subject identifier")
    email: Optional[EmailStr] = Field(None, description="User email")
    email_verified: bool = Field(False, description="Email verification status")
    name: Optional[str] = Field(None, description="User display name")
    preferred_username: Optional[str] = Field(None, description="Preferred username")
    given_name: Optional[str] = Field(None, description="First name")
    family_name: Optional[str] = Field(None, description="Last name")

class TokenResponse(BaseModel):
    """OAuth2 token response."""
    
    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field("Bearer", description="Token type")
    expires_in: int = Field(..., description="Token expiration in seconds")
    refresh_token: Optional[str] = Field(None, description="Refresh token")
    id_token: Optional[str] = Field(None, description="OIDC ID token")
    scope: Optional[str] = Field(None, description="Granted scopes")

class AuthorizationRequest(BaseModel):
    """Authorization request parameters."""
    
    redirect_uri: Optional[str] = Field(
        None,
        description="Custom redirect URI"
    )
    state: Optional[str] = Field(None, description="CSRF state parameter")

class AuthorizationCallback(BaseModel):
    """Authorization callback parameters."""
    
    code: str = Field(..., description="Authorization code")
    state: Optional[str] = Field(None, description="CSRF state parameter")

class RefreshTokenRequest(BaseModel):
    """Refresh token request."""
    
    refresh_token: str = Field(..., description="Refresh token")

class UserProfileResponse(BaseModel):
    """User profile response."""
    
    id: uuid.UUID = Field(..., description="User ID")
    oidc_sub: str = Field(..., description="OIDC subject identifier")
    email: str = Field(..., description="User email")
    name: str = Field(..., description="User display name")
    role: UserRole = Field(..., description="User role")
    created_at: datetime = Field(..., description="Account creation time")
    updated_at: datetime = Field(..., description="Last update time")
    
    class Config:
        """Pydantic configuration."""
        
        from_attributes = True

class LoginResponse(BaseModel):
    """Login response with tokens and user profile."""
    
    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field("Bearer", description="Token type")
    expires_in: int = Field(..., description="Token expiration in seconds")
    refresh_token: Optional[str] = Field(None, description="Refresh token")
    user: UserProfileResponse = Field(..., description="User profile")

class AuthErrorResponse(BaseModel):
    """Authentication error response."""
    
    error: str = Field(..., description="Error code")
    error_description: str = Field(..., description="Error description")