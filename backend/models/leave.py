from sqlalchemy import Column, Integer, String, Date
from db.database import Base

class LeaveRequest(Base):
    __tablename__ = "leave_requests"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    reason = Column(String, nullable=True)
    status = Column(String, nullable=False,default="pending",)
    leave_type = Column(String, nullable=False, default="casual")
    total_days = Column(Integer, nullable=False, default=1)
    manager_email = Column(String, nullable=True)

