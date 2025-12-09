from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.shared.models.user import User


class UserRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_by_id(self, user_id: uuid.UUID) -> User | None:
        return self.session.get(User, user_id)

    def upsert_oidc_user(
        self,
        sub: str,
        email: str,
        name: str,
        role: str | None,
        last_login_ip: str | None = None,
        user_agent: str | None = None,
    ) -> User:
        stmt = select(User).where(User.oidc_sub == sub)
        user = self.session.scalars(stmt).first()
        if user is None:
            user = User(
                oidc_sub=sub,
                email=email,
                name=name,
                role=role or "viewer",
                last_login_ip=last_login_ip,
                last_login_user_agent=user_agent,
            )
            self.session.add(user)
        else:
            user.email = email
            user.name = name
            user.role = role or user.role
            user.last_login_ip = last_login_ip
            user.last_login_user_agent = user_agent
        self.session.commit()
        self.session.refresh(user)
        return user