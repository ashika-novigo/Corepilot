from sqlalchemy import Column, Integer, String, Text, DateTime
from datetime import datetime, timezone
from db.database import Base


class Ticket(Base):
    __tablename__ = "tickets"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, nullable=False)
    issue_type = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    priority = Column(String, nullable=False, default="medium")
    status = Column(String, nullable=False, default="open")
    assigned_engineer = Column(String, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc)) 
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))