from sqlalchemy import Column, Integer

from db.database import Base


class LeaveBalance(Base):
    __tablename__ = "leave_balances"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, unique=True, nullable=False, index=True)
    sick_total = Column(Integer, nullable=False, default=6)
    sick_used = Column(Integer, nullable=False, default=0)
    casual_total = Column(Integer, nullable=False, default=6)
    casual_used = Column(Integer, nullable=False, default=0)
    earned_total = Column(Integer, nullable=False, default=12)
    earned_used = Column(Integer, nullable=False, default=0)
