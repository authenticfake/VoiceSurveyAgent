from enum import Enum
from uuid import UUID

from pydantic import BaseModel, EmailStr


class Role(str, Enum):
    admin = "admin"
    campaign_manager = "campaign_manager"
    viewer = "viewer"


class UserPrincipal(BaseModel):
    id: UUID
    email: EmailStr
    role: Role