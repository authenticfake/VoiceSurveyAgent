from pydantic import BaseModel, HttpUrl, validator

from app.auth.domain.models import Role, User
from app.auth.domain.service import AuthResult


class OIDCCallbackRequest(BaseModel):
    code: str
    redirect_uri: HttpUrl
    code_verifier: str | None = None
    state: str | None = None

    @validator("code", "redirect_uri")
    def non_empty(cls, v: str) -> str:
        if not v:
            raise ValueError("value must not be empty")
        return v


class UserView(BaseModel):
    id: str
    email: str
    name: str
    role: Role

    @classmethod
    def from_domain(cls, user: User) -> "UserView":
        return cls(id=str(user.id), email=user.email, name=user.name, role=user.role)


class TokenView(BaseModel):
    access_token: str
    id_token: str
    expires_in: int
    refresh_token: str | None = None
    token_type: str = "Bearer"


class LoginResponse(BaseModel):
    user: UserView
    tokens: TokenView

    @classmethod
    def from_result(cls, result: AuthResult) -> "LoginResponse":
        return cls(
            user=UserView.from_domain(result.user),
            tokens=TokenView(
                access_token=result.token_set.access_token,
                id_token=result.token_set.id_token,
                refresh_token=result.token_set.refresh_token,
                expires_in=result.token_set.expires_in,
                token_type=result.token_set.token_type,
            ),
        )