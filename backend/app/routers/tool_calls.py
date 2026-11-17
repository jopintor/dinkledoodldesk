from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.deps import get_current_user, get_db, not_found
from app.models import ToolCall, User
from app.tools.executor import run_create_ticket, tool_call_out

router = APIRouter(prefix="/api/v1/tool-calls", tags=["tool-calls"])


def _owned(db: Session, user: User, tool_call_id: int) -> ToolCall:
    """Someone else's tool call looks exactly like one that doesn't exist (404)."""
    tool_call = db.get(ToolCall, tool_call_id)
    if tool_call is None or tool_call.user_id != user.id:
        raise not_found()
    return tool_call


def _response(tool_call: ToolCall, message: str) -> dict:
    # TODO: match the response shape in the API doc / frontend types.
    return {**tool_call_out(tool_call), "result": tool_call.result, "message": message}


@router.post("/{tool_call_id}/confirm")
def confirm_tool_call(
    tool_call_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    tool_call = _owned(db, user, tool_call_id)
    if tool_call.status != "awaiting_confirmation":
        raise HTTPException(status.HTTP_409_CONFLICT, "This action was already handled.")

    if tool_call.tool_name != "create_ticket":
        raise HTTPException(status.HTTP_409_CONFLICT, "That action isn't available yet.")

    try:
        result = run_create_ticket(db, user, tool_call.arguments)
        tool_call.status = "succeeded"
        tool_call.result = result
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        tool_call = db.get(ToolCall, tool_call_id)
        tool_call.status = "failed"
        tool_call.result = {"error": "Could not save the ticket."}
        db.commit()
        return _response(tool_call, "Sorry, I couldn't create the ticket.")

    return _response(tool_call, f"Ticket {result['ticket_number']} created.")


@router.post("/{tool_call_id}/cancel")
def cancel_tool_call(
    tool_call_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    tool_call = _owned(db, user, tool_call_id)
    if tool_call.status != "awaiting_confirmation":
        raise HTTPException(status.HTTP_409_CONFLICT, "This action was already handled.")

    tool_call.status = "cancelled"
    db.commit()
    return _response(tool_call, "Okay, I didn't change anything.")
