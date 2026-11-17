"""Read-only data for the admin dashboard (escalations and a few real counts)."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.deps import get_current_user, get_db
from app.guardrails.events import get_guardrail_log
from app.models import Role, Ticket, User

router = APIRouter(prefix="/api/v1", tags=["admin"])

# A ticket counts as an escalation when it is urgent or already marked escalated.
ESCALATION_PRIORITIES = ("P1", "P2")
ESCALATED_STATUS = "escalated"

# Dashboard numbers we can't compute yet. They are returned as null, never invented.
# TODO: replace with the other field names in MetricsSummary (frontend/src/lib/types.ts).
NOT_COMPUTED_YET = ("auto_resolution_rate", "avg_first_response_seconds", "csat")


def require_agent_or_admin(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> User:
    role = db.get(Role, user.role_id)
    if role is None or role.name not in ("agent", "admin"):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not allowed")
    return user


# ---- guardrail log ----------------------------------------------------------
def _raw_guardrail_events() -> list:
    """The events the GET /guardrail-events route returns.

    TODO: use the same call the /guardrail-events route makes. Find it with:
        grep -rn "guardrail-events" backend/app
    """
    return list(get_guardrail_log().list_events())


def _field(raw, *names):
    """Read the first of several possible field names from a dict or an object."""
    for name in names:
        value = raw.get(name) if isinstance(raw, dict) else getattr(raw, name, None)
        if value is not None:
            return value
    return None


def _normalise_event(raw) -> dict:
    """One guardrail event in a fixed shape.

    TODO: check the field names and the kind names against
    backend/app/guardrails/events.py.
    """
    kind = str(_field(raw, "kind", "event_type", "type", "rule") or "")
    action = str(_field(raw, "action", "action_taken") or "")
    created = _field(raw, "created_at", "timestamp", "ts", "at")
    text = f"{kind} {action}".lower()
    return {
        "id": _field(raw, "id", "event_id"),
        "kind": kind,
        "detail": _field(raw, "detail", "details", "message", "reason"),
        "created_at": created.isoformat() if hasattr(created, "isoformat") else created,
        "is_escalation": any(word in text for word in ("escalat", "handoff", "human")),
        "is_block": "block" in text,
    }


def _events() -> list[dict]:
    return [_normalise_event(raw) for raw in _raw_guardrail_events()]


# ---- shapes -----------------------------------------------------------------
def _escalated_tickets():
    return or_(
        Ticket.priority.in_(ESCALATION_PRIORITIES),
        Ticket.status == ESCALATED_STATUS,
    )


def escalation_from_ticket(t: Ticket) -> dict:
    # TODO: match the Escalation shape in frontend/src/lib/types.ts.
    return {
        "id": t.id,
        "source": "ticket",
        "ticket_number": t.ticket_number,
        "summary": t.summary,
        "priority": t.priority,
        "status": t.status,
        "reason": "escalated" if t.status == ESCALATED_STATUS else f"{t.priority} priority",
        "category": t.category,
        "affected_system": t.affected_system,
        "club_code": t.club_code,
        "created_at": t.created_at.isoformat() if t.created_at else None,
    }


def escalation_from_event(e: dict) -> dict:
    # TODO: match the Escalation shape in frontend/src/lib/types.ts.
    return {
        "id": e["id"],
        "source": "guardrail",
        "ticket_number": None,
        "summary": e["detail"] or e["kind"],
        "priority": None,
        "status": None,
        "reason": e["kind"],
        "category": None,
        "affected_system": None,
        "club_code": None,
        "created_at": e["created_at"],
    }


# ---- endpoints --------------------------------------------------------------
@router.get("/escalations")
def list_escalations(
    user: User = Depends(require_agent_or_admin),
    db: Session = Depends(get_db),
):
    tickets = db.scalars(
        select(Ticket).where(_escalated_tickets()).order_by(Ticket.id.desc())
    ).all()
    items = [escalation_from_ticket(t) for t in tickets]
    items += [escalation_from_event(e) for e in _events() if e["is_escalation"]]
    items.sort(key=lambda item: item["created_at"] or "", reverse=True)
    return {"items": items, "next_cursor": None}


@router.get("/metrics/summary")
def metrics_summary(
    user: User = Depends(require_agent_or_admin),
    db: Session = Depends(get_db),
):
    tickets_created = db.scalar(select(func.count()).select_from(Ticket)) or 0
    escalated_tickets = (
        db.scalar(select(func.count()).select_from(Ticket).where(_escalated_tickets())) or 0
    )
    events = _events()

    # TODO: match the MetricsSummary shape in frontend/src/lib/types.ts.
    summary = {
        "tickets_created": tickets_created,
        "escalations": escalated_tickets + sum(e["is_escalation"] for e in events),
        "guardrail_blocks": sum(e["is_block"] for e in events),
    }
    summary.update({name: None for name in NOT_COMPUTED_YET})
    return summary
