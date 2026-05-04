from sqlalchemy import Column, Integer, String, DateTime
from datetime import datetime, timezone
from db.database import Base


class Employee(Base):
    __tablename__ = "employees"

    id = Column(Integer, primary_key=True, index=True)

    name = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False)

    role = Column(String, nullable=False, default="employee")
    department = Column(String, nullable=True)

    manager_id = Column(Integer, nullable=True)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))