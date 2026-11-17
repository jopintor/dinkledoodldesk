from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Ticket(Base):
    __tablename__ = "tickets"

    id: Mapped[int] = mapped_column(primary_key=True)
    ticket_number: Mapped[str | None] = mapped_column(String(20), unique=True)
    summary: Mapped[str] = mapped_column(String(120))
    description: Mapped[str | None] = mapped_column(Text)
    category: Mapped[str] = mapped_column(String(40))
    affected_system: Mapped[str] = mapped_column(String(40))
    priority: Mapped[str] = mapped_column(String(10), default="P3")
    status: Mapped[str] = mapped_column(String(30), default="open")
    requester_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    club_code: Mapped[str | None] = mapped_column(String(10))
    jira_key: Mapped[str | None] = mapped_column(String(30))
    jira_sync_status: Mapped[str] = mapped_column(String(20), default="pending")
    conversation_id: Mapped[int | None] = mapped_column(ForeignKey("conversations.id"))
    assigned_to: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
