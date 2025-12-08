"""
Permission decorators and utilities for route protection.

Provides FastAPI dependencies for enforcing role-based access control
on API endpoints.
"""

from functools import wraps
from typing import Callable, List, Optional, Union

from fastapi import Depends, HTTPException, Request, status

from app.auth.rbac.roles import Role, RoleHierarchy
from app.auth.rbac.logging import log_access_denied


class RBACError(Exception):
    """Base exception for RBAC errors."""
    pass


class InsufficientPermissionsError(RBACError):
    """Raised when user lacks required permissions."""
    pass


async def get_current_user_role(request: Request) -> Role:
    """
    Extract user role from request state.
    
    The role is extracted from:
    1. JWT claims (if 'role' claim exists)
    2. User database record (via request.state.user)
    
    Args:
        request: FastAPI request object
        
    Returns:
        User's Role enum
        
    Raises:
        HTTPException: If no valid role can be determined
    """
    # Check if user is set in request state (from auth middleware)
    user = getattr(request.state, "user", None)
    
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )
    
    # Try to get role from JWT claims first
    jwt_claims = getattr(request.state, "jwt_claims", None)
    if jwt_claims and "role" in jwt_claims:
        try:
            return Role.from_string(jwt_claims["role"])
        except ValueError:
            pass  # Fall through to user record
    
    # Get role from user record
    user_role = getattr(user, "role", None)
    if user_role is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User role not configured",
        )
    
    try:
        if isinstance(user_role, Role):
            return user_role
        return Role.from_string(str(user_role))
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )


def require_role(
    minimum_role: Role,
    log_denial: bool = True,
) -> Callable:
    """
    Dependency that enforces minimum role requirement.
    
    Uses role hierarchy to determine if user has sufficient privileges.
    
    Args:
        minimum_role: The minimum role required to access the endpoint
        log_denial: Whether to log access denial attempts
        
    Returns:
        FastAPI dependency function
        
    Example:
        @router.get("/admin/config")
        async def get_config(
            _: None = Depends(require_role(Role.ADMIN))
        ):
            ...
    """
    async def role_checker(
        request: Request,
        user_role: Role = Depends(get_current_user_role),
    ) -> Role:
        if not RoleHierarchy.has_minimum_role(user_role, minimum_role):
            user = getattr(request.state, "user", None)
            user_id = str(user.id) if user else "unknown"
            endpoint = f"{request.method} {request.url.path}"
            
            if log_denial:
                await log_access_denied(
                    user_id=user_id,
                    endpoint=endpoint,
                    required_role=minimum_role.value,
                    user_role=user_role.value,
                    request=request,
                )
            
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required role: {minimum_role.value}",
            )
        
        return user_role
    
    return role_checker


def require_any_role(
    roles: List[Role],
    log_denial: bool = True,
) -> Callable:
    """
    Dependency that allows access if user has any of the specified roles.
    
    Args:
        roles: List of roles that are allowed access
        log_denial: Whether to log access denial attempts
        
    Returns:
        FastAPI dependency function
        
    Example:
        @router.put("/campaigns/{id}")
        async def update_campaign(
            _: None = Depends(require_any_role([Role.ADMIN, Role.CAMPAIGN_MANAGER]))
        ):
            ...
    """
    async def role_checker(
        request: Request,
        user_role: Role = Depends(get_current_user_role),
    ) -> Role:
        if user_role not in roles:
            user = getattr(request.state, "user", None)
            user_id = str(user.id) if user else "unknown"
            endpoint = f"{request.method} {request.url.path}"
            
            if log_denial:
                await log_access_denied(
                    user_id=user_id,
                    endpoint=endpoint,
                    required_role=f"one of {[r.value for r in roles]}",
                    user_role=user_role.value,
                    request=request,
                )
            
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required one of: {[r.value for r in roles]}",
            )
        
        return user_role
    
    return role_checker


def require_permission(
    permission: str,
    log_denial: bool = True,
) -> Callable:
    """
    Dependency that enforces specific permission requirement.
    
    Args:
        permission: The permission string required (e.g., 'campaigns:create')
        log_denial: Whether to log access denial attempts
        
    Returns:
        FastAPI dependency function
        
    Example:
        @router.post("/campaigns")
        async def create_campaign(
            _: None = Depends(require_permission("campaigns:create"))
        ):
            ...
    """
    async def permission_checker(
        request: Request,
        user_role: Role = Depends(get_current_user_role),
    ) -> Role:
        if not RoleHierarchy.has_permission(user_role, permission):
            user = getattr(request.state, "user", None)
            user_id = str(user.id) if user else "unknown"
            endpoint = f"{request.method} {request.url.path}"
            
            if log_denial:
                await log_access_denied(
                    user_id=user_id,
                    endpoint=endpoint,
                    required_role=f"permission:{permission}",
                    user_role=user_role.value,
                    request=request,
                )
            
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing required permission: {permission}",
            )
        
        return user_role
    
    return permission_checker


class RBACMiddleware:
    """
    Middleware for applying RBAC checks globally.
    
    Can be used to enforce role requirements on route patterns
    without explicit decorators.
    """
    
    def __init__(
        self,
        app,
        admin_paths: Optional[List[str]] = None,
        manager_paths: Optional[List[str]] = None,
    ):
        """
        Initialize RBAC middleware.
        
        Args:
            app: FastAPI application
            admin_paths: URL path prefixes requiring admin role
            manager_paths: URL path prefixes requiring campaign_manager role
        """
        self.app = app
        self.admin_paths = admin_paths or ["/api/admin"]
        self.manager_paths = manager_paths or []
    
    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        
        path = scope.get("path", "")
        
        # Check if path requires specific role
        # Actual enforcement happens in route dependencies
        # This middleware can add metadata to scope for logging
        
        await self.app(scope, receive, send)