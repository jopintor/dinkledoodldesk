from collections.abc import Generator

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.models import Role, User
from app.permissions import has_permission
from app.security import decode_token

bearer = HTTPBearer(auto_error=False)


def get_db() -> Generator[Session, None, None]:
    with SessionLocal() as session:
        yield session


def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
) -> User:
    unauthorized = HTTPException(status.HTTP_401_UNAUTHORIZED, "Not authenticated")
    if creds is None:
        raise unauthorized
    try:
        payload = decode_token(creds.credentials)
    except jwt.PyJWTError:
        raise unauthorized from None
    user = db.get(User, int(payload["sub"]))
    if user is None or not user.is_active:
        raise unauthorized
    return user


def require(permission: str):
    """Use on any route: user = Depends(require("ticket:create"))"""

    def checker(
        user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
    ) -> User:
        role = db.get(Role, user.role_id)
        if role is None or not has_permission(role.name, permission):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Not allowed")
        return user

    return checker


def not_found() -> HTTPException:
    """Use when something exists but isn't the caller's (requirement 6)."""
    return HTTPException(status.HTTP_404_NOT_FOUND, "Not found")
