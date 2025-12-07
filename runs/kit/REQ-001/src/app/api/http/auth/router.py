from fastapi import APIRouter, Depends

from app.api.http.errors import APIError
from app.auth.domain.models import Role, User
from app.auth.domain.service import AuthService
from app.auth.rbac import RBACDependencies
from app.auth.schemas import AuthenticatedUserResponse
from app.api.http.auth.schemas import LoginResponse, OIDCCallbackRequest, UserView


def build_auth_router(
    auth_service: AuthService,
    rbac: RBACDependencies,
) -> APIRouter:
    router = APIRouter(prefix="/api/auth", tags=["auth"])

    @router.post(
        "/oidc/callback",
        response_model=LoginResponse,
        responses={400: {"model": APIError}},
    )
    async def oidc_callback(payload: OIDCCallbackRequest) -> LoginResponse:
        result = await auth_service.complete_login(payload)
        return LoginResponse.from_result(result)

    @router.get(
        "/me",
        response_model=AuthenticatedUserResponse,
        responses={401: {"model": APIError}},
    )
    async def who_am_i(user: User = Depends(rbac.current_user)) -> AuthenticatedUserResponse:
        return AuthenticatedUserResponse.from_domain(user)

    @router.get(
        "/admin/ping",
        dependencies=[Depends(rbac.require_roles(Role.admin))],
        responses={401: {"model": APIError}, 403: {"model": APIError}},
    )
    async def admin_ping() -> dict[str, str]:
        return {"status": "ok"}

    return router