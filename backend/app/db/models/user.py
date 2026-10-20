import uuid
from datetime import UTC, datetime

from sqlalchemy import Column, DateTime, String

from app.db.database import Base


def _uuid():
    return str(uuid.uuid4())[:8]


class User(Base):
    """Minimal for now — real auth is deliberately deprioritized until
    the CV system works. Enough to satisfy the FK/table if auth routes
    get stubbed in later."""

    __tablename__ = "users"

    id = Column(String, primary_key=True, default=_uuid)
    email = Column(String, unique=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))