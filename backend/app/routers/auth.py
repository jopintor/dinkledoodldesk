from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.deps import get_current_user, get_db
from app.models import AuditLog, Role, User
from app.security import (
    DUMMY_HASH,
    create_token,
    settings,
    verify_password,
)

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

MAX_FAILURES = 5
WINDOW = timedelta(minutes=15)
LOCK = timedelta(minutes=15)


class LoginRequest(BaseModel):
    email: str
    password: str


def _audit(db: Session, user_id: int | None, action: str, details: dict) -> None:
    db.add(AuditLog(user_id=user_id, action=action, details=details))


def _is_locked(db: Session, user_id: int) -> bool:
    last_ok = db.scalar(
        select(func.max(AuditLog.created_at)).where(
            AuditLog.user_id == user_id, AuditLog.action == "login_success"
        )
    )
    query = select(AuditLog.created_at).where(
        AuditLog.user_id == user_id, AuditLog.action == "login_failed"
    )
    if last_ok is not None:
        query = query.where(AuditLog.created_at > last_ok)
    failures = db.scalars(query.order_by(AuditLog.created_at.desc()).limit(MAX_FAILURES)).all()

    if len(failures) < MAX_FAILURES:
        return False
    latest, oldest = failures[0], failures[-1]
    within_window = (latest - oldest) <= WINDOW
    still_locked = datetime.now(UTC) < latest + LOCK
    return within_window and still_locked


@router.post("/login")
def login(body: LoginRequest, request: Request, db: Session = Depends(get_db)):
    email = body.email.strip().lower()
    ip = request.client.host if request.client else None
    invalid = HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid email or password")

    user = db.scalar(select(User).where(func.lower(User.email) == email))

    if user is None or not user.is_active:
        verify_password(DUMMY_HASH, body.password)  # keep timing similar
        _audit(db, user.id if user else None, "login_failed", {"email": email, "ip": ip})
        db.commit()
        raise invalid

    if _is_locked(db, user.id):
        _audit(db, user.id, "login_locked", {"email": email, "ip": ip})
        db.commit()
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            "Too many failed attempts. Try again in 15 minutes.",
        )

    if not verify_password(user.password_hash, body.password):
        _audit(db, user.id, "login_failed", {"email": email, "ip": ip})
        db.commit()
        raise invalid

    role = db.get(Role, user.role_id)
    _audit(db, user.id, "login_success", {"email": email, "ip": ip})
    db.commit()

    # TODO: match the response shape in API doc section 3.
    return {
        "access_token": create_token(user.id, role.name),
        "token_type": "bearer",
        "expires_in": settings.jwt_expires_min * 60,
    }


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # Tokens are stateless, so the client just discards its token.
    _audit(db, user.id, "logout", {})
    db.commit()


@router.get("/me")
def me(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    role = db.get(Role, user.role_id)
    # TODO: match the response shape in API doc section 3.
    return {
        "id": user.id,
        "email": user.email,
        "full_name": user.full_name,
        "role": role.name if role else None,
        "club_id": user.club_id,
    }
