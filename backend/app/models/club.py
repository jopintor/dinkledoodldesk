from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Club(Base):
    __tablename__ = "clubs"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(10), unique=True)
    name: Mapped[str] = mapped_column(String(120))
