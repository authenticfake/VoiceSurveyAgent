from fastapi import HTTPException, status
from pydantic import BaseModel


class APIError(BaseModel):
    code: str
    message: str


def http_error(status_code: int, code: str, message: str) -> HTTPException:
    return HTTPException(status_code=status_code, detail={"code": code, "message": message})


def unauthorized(message: str = "Authentication required") -> HTTPException:
    return http_error(status.HTTP_401_UNAUTHORIZED, "auth.unauthorized", message)


def forbidden(message: str = "Insufficient role") -> HTTPException:
    return http_error(status.HTTP_403_FORBIDDEN, "auth.forbidden", message)