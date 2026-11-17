"""Read-only data for the agent queue and the admin dashboard.

- `router`: `GET /api/v1/escalations` in the `Escalation` shape of frontend/src/lib/types.ts.
  Rows come from urgent/escalated tickets and from `escalated` guardrail events.
- `metrics_router`: `GET /api/v1/metrics/summary` with the few counts the backend really
  has. Not registered in app/main.py yet: the dashboard needs the full `MetricsSummary`
  shape (deflection, MTTR, latency...), which nothing records yet, so the frontend keeps
  its mock numbers until those exist.
"""

from datetime import UTC, datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.deps import get_current_user, get_db
from app.guardrails.events import GuardrailEventRecord, GuardrailLog, get_guardrail_log
from app.models import Role, Ticket, User

router = APIRouter(prefix="/api/v1", tags=["admin"])
metrics_router = APIRouter(prefix="/api/v1", tags=["admin"])

# A ticket counts as an escalation when it is urgent or already marked escalated.
ESCALATION_PRIORITIES = ("P1", "P2")
ESCALATED_STATUS = "escalated"
CLOSED_STATUSES = ("resolved", "closed")

# How many guardrail events the queue and the counts look at.
EVENT_WINDOW = 500

# Dashboard numbers we can't compute yet. They are returned as null, never invented.
NOT_COMPUTED_YET = ("auto_resolution_rate", "avg_first_response_seconds", "csat")


def require_agent_or_admin(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> User:
    role = db.get(Role, user.role_id)
    if role is None or role.name not in ("agent", "admin"):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not allowed")
    return user


def _label(code: str | None) -> str:
    return (code or "other").replace("_", " ").capitalize()


def _iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None:  # SQLite drops the timezone; stored values are UTC.
        value = value.replace(tzinfo=UTC)
    return value.isoformat()


def _waiting_s(created: datetime | None, now: datetime) -> int:
    if created is None:
        return 0
    if created.tzinfo is None:
        created = created.replace(tzinfo=UTC)
    return max(0, int((now - created).total_seconds()))


def _person(user: User | None, db: Session, role_hint: str | None = None) -> dict:
    role = db.get(Role, user.role_id) if user else None
    return {
        "full_name": user.full_name if user else "Unknown user",
        "role": role.name if role else (role_hint or "staff"),
        "club_code": None,
    }


# ---- shapes (frontend/src/lib/types.ts `Escalation`) ------------------------
def escalation_from_ticket(t: Ticket, db: Session, now: datetime) -> dict:
    requester = db.get(User, t.requester_id)
    assignee = db.get(User, t.assigned_to) if t.assigned_to else None
    if t.status in CLOSED_STATUSES:
        state = "resolved"
    elif assignee is not None:
        state = "assigned"
    else:
        state = "queued"
    return {
        "id": f"t-{t.id}",
        "source": "ticket",
        "conversation_id": str(t.conversation_id) if t.conversation_id else "",
        "ticket_number": t.ticket_number or "",
        "reason": "escalated" if t.status == ESCALATED_STATUS else f"{t.priority} priority",
        "urgency": "high" if t.priority in ESCALATION_PRIORITIES else "normal",
        "handoff_summary": t.description or t.summary,
        "user": {**_person(requester, db), "club_code": t.club_code},
        "status": state,
        "created_at": _iso(t.created_at),
        "waiting_s": _waiting_s(t.created_at, now),
        "title": t.summary,
        "priority": t.priority,
        "jira_key": t.jira_key,
        "category_label": _label(t.category),
        "assigned_agent": (
            {"id": str(assignee.id), "full_name": assignee.full_name} if assignee else None
        ),
    }


def escalation_from_event(e: GuardrailEventRecord, db: Session, now: datetime) -> dict:
    user = db.get(User, e.user_id) if e.user_id is not None else None
    reason = _label(e.type)
    return {
        "id": f"g-{e.id}",
        "source": "guardrail",
        "conversation_id": str(e.conversation_id) if e.conversation_id else "",
        "ticket_number": "",
        "reason": e.type,
        "urgency": "normal",
        "handoff_summary": f"The assistant handed this chat to IT ({reason.lower()}).",
        "user": _person(user, db, e.user_role),
        "status": "queued",
        "created_at": _iso(e.created_at),
        "waiting_s": _waiting_s(e.created_at, now),
        "title": f"Escalated chat: {reason.lower()}",
        "priority": "P3",
        "jira_key": None,
        "category_label": reason,
        "assigned_agent": None,
    }


def _escalated_tickets():
    return or_(
        Ticket.priority.in_(ESCALATION_PRIORITIES),
        Ticket.status == ESCALATED_STATUS,
    )


def _events(log: GuardrailLog) -> list[GuardrailEventRecord]:
    return list(log.recent(limit=EVENT_WINDOW))


# ---- endpoints --------------------------------------------------------------
@router.get("/escalations")
def list_escalations(
    status_filter: Literal["open", "resolved", "all"] = Query("open", alias="status"),
    user: User = Depends(require_agent_or_admin),
    db: Session = Depends(get_db),
    guardrail_log: GuardrailLog = Depends(get_guardrail_log),
):
    now = datetime.now(UTC)
    tickets = db.scalars(
        select(Ticket).where(_escalated_tickets()).order_by(Ticket.id.desc())
    ).all()
    items = [escalation_from_ticket(t, db, now) for t in tickets]
    items += [
        escalation_from_event(e, db, now) for e in _events(guardrail_log) if e.action == "escalated"
    ]
    if status_filter == "open":
        items = [i for i in items if i["status"] != "resolved"]
    elif status_filter == "resolved":
        items = [i for i in items if i["status"] == "resolved"]
    items.sort(key=lambda item: item["created_at"] or "", reverse=True)
    return {"items": items, "next_cursor": None}


@metrics_router.get("/metrics/summary")
def metrics_summary(
    user: User = Depends(require_agent_or_admin),
    db: Session = Depends(get_db),
    guardrail_log: GuardrailLog = Depends(get_guardrail_log),
):
    tickets_created = db.scalar(select(func.count()).select_from(Ticket)) or 0
    escalated_tickets = (
        db.scalar(select(func.count()).select_from(Ticket).where(_escalated_tickets())) or 0
    )
    events = _events(guardrail_log)
    summary = {
        "tickets_created": tickets_created,
        "escalations": escalated_tickets + sum(e.action == "escalated" for e in events),
        "guardrail_blocks": sum(e.action == "blocked" for e in events),
    }
    summary.update({name: None for name in NOT_COMPUTED_YET})
    return summary
