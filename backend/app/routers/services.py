from typing import Literal

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.deps import get_current_user, get_db, not_found, require
from app.models import AuditLog, ServiceStatus, User
from app.ratelimit import limiter
from app.utils import slugify

router = APIRouter(prefix="/api/v1/services", tags=["services"])

# Same values as `ServiceState` in frontend/src/lib/types.ts.
ServiceState = Literal[
    "operational", "degraded_performance", "partial_outage", "major_outage", "maintenance"
]


class StatusUpdate(BaseModel):
    status: ServiceState


def service_out(s: ServiceStatus) -> dict:
    """`ServiceStatus` in frontend/src/lib/types.ts."""
    return {
        "service_key": slugify(s.service_name),
        "display_name": s.service_name,
        "status": s.status,
        "club_code": None,
        "message": None,
        "updated_at": s.updated_at,
    }


@router.get("/status")
@limiter.limit("60/minute")
def list_service_status(
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    rows = db.scalars(select(ServiceStatus).order_by(ServiceStatus.service_name)).all()
    return {"items": [service_out(s) for s in rows]}


@router.put("/{service_key}/status")
@limiter.limit("20/minute")
def update_service_status(
    request: Request,
    service_key: str,
    body: StatusUpdate,
    user: User = Depends(require("status:update")),  # admins only
    db: Session = Depends(get_db),
):
    rows = db.scalars(select(ServiceStatus)).all()
    service = next((s for s in rows if slugify(s.service_name) == service_key), None)
    if service is None:
        raise not_found()

    old_status = service.status
    service.status = body.status
    db.add(
        AuditLog(
            user_id=user.id,
            action="service_status_updated",
            details={"service": service_key, "from": old_status, "to": body.status},
        )
    )
    db.commit()
    db.refresh(service)
    return service_out(service)
