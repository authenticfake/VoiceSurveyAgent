"""Authentication service for user management."""
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.config import AuthConfig
from app.auth.jwt_validator import JWTValidator
from app.auth.jwks import JWKSClient
from app.auth.models import TokenPayload, UserInfo
from app.auth.oidc_client import OIDCClient
from app.shared.models.enums import UserRole
from app.shared.models.user import User

class AuthService:
    """Service for authentication and user management."""
    
    def __init__(
        self,
        config: AuthConfig,
        oidc_client: OIDCClient,
        jwt_validator: JWTValidator
    ) -> None:
        """Initialize authentication service.
        
        Args:
            config: Authentication configuration
            oidc_client: OIDC client for authorization flow
            jwt_validator: JWT validator for token validation
        """
        self._config = config
        self._oidc_client = oidc_client
        self._jwt_validator = jwt_validator
    
    @classmethod
    def create(cls, config: AuthConfig) -> "AuthService":
        """Factory method to create AuthService with dependencies.
        
        Args:
            config: Authentication configuration
            
        Returns:
            Configured AuthService instance
        """
        jwks_client = JWKSClient(config.jwks_uri)
        oidc_client = OIDCClient(config)
        jwt_validator = JWTValidator(config, jwks_client)
        return cls(config, oidc_client, jwt_validator)
    
    def generate_state(self) -> str:
        """Generate CSRF state parameter.
        
        Returns:
            Random state string
        """
        return self._oidc_client.generate_state()
    
    def get_authorization_url(
        self,
        state: str,
        redirect_uri: Optional[str] = None
    ) -> str:
        """Get authorization URL for OIDC flow.
        
        Args:
            state: CSRF state parameter
            redirect_uri: Optional custom redirect URI
            
        Returns:
            Authorization URL
        """
        return self._oidc_client.get_authorization_url(state, redirect_uri)
    
    async def validate_token(self, token: str) -> TokenPayload:
        """Validate JWT token.
        
        Args:
            token: JWT token string
            
        Returns:
            Validated token payload
        """
        return await self._jwt_validator.validate_token(token)
    
    async def exchange_code_and_get_user(
        self,
        code: str,
        db: AsyncSession,
        redirect_uri: Optional[str] = None
    ) -> tuple[User, str, Optional[str]]:
        """Exchange authorization code and create/update user.
        
        Args:
            code: Authorization code
            db: Database session
            redirect_uri: Redirect URI used in authorization
            
        Returns:
            Tuple of (user, access_token, refresh_token)
        """
        # Exchange code for tokens
        token_response = await self._oidc_client.exchange_code(
            code,
            redirect_uri
        )
        
        # Get user info from provider
        user_info = await self._oidc_client.get_userinfo(
            token_response.access_token
        )
        
        # Create or update user in database
        user = await self._get_or_create_user(db, user_info)
        
        return (
            user,
            token_response.access_token,
            token_response.refresh_token
        )
    
    async def refresh_tokens(
        self,
        refresh_token: str
    ) -> tuple[str, Optional[str]]:
        """Refresh access token.
        
        Args:
            refresh_token: Refresh token
            
        Returns:
            Tuple of (new_access_token, new_refresh_token)
        """
        token_response = await self._oidc_client.refresh_tokens(refresh_token)
        return (
            token_response.access_token,
            token_response.refresh_token
        )
    
    async def get_user_by_sub(
        self,
        db: AsyncSession,
        oidc_sub: str
    ) -> Optional[User]:
        """Get user by OIDC subject identifier.
        
        Args:
            db: Database session
            oidc_sub: OIDC subject identifier
            
        Returns:
            User if found, None otherwise
        """
        result = await db.execute(
            select(User).where(User.oidc_sub == oidc_sub)
        )
        return result.scalar_one_or_none()
    
    async def _get_or_create_user(
        self,
        db: AsyncSession,
        user_info: UserInfo
    ) -> User:
        """Get existing user or create new one.
        
        Args:
            db: Database session
            user_info: User information from OIDC provider
            
        Returns:
            User record
        """
        # Try to find existing user
        user = await self.get_user_by_sub(db, user_info.sub)
        
        if user:
            # Update user info if changed
            updated = False
            if user_info.email and user.email != user_info.email:
                user.email = user_info.email
                updated = True
            if user_info.name and user.name != user_info.name:
                user.name = user_info.name
                updated = True
            
            if updated:
                user.updated_at = datetime.now(timezone.utc)
                await db.commit()
                await db.refresh(user)
        else:
            # Create new user with default viewer role
            user = User(
                id=uuid.uuid4(),
                oidc_sub=user_info.sub,
                email=user_info.email or f"{user_info.sub}@unknown",
                name=user_info.name or user_info.preferred_username or "Unknown",
                role=UserRole.VIEWER,
            )
            db.add(user)
            await db.commit()
            await db.refresh(user)
        
        return user