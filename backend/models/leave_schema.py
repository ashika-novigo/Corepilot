from pydantic import BaseModel
from datetime import date

class LeaveCreate(BaseModel):
    employee_id: str
    start_date: date
    end_date: date
    reason: str | None = None
    leave_type: str = "casual"

class LeaveResponse(BaseModel):
    id: int
    employee_id: str
    start_date: date
    end_date: date
    reason: str | None
    status: str
    leave_type: str
    total_days: int


    class Config:
        from_attributes = True

