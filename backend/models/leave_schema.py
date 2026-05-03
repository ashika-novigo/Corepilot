from pydantic import BaseModel
from datetime import date

class LeaveCreate(BaseModel):
    employee_id: str
    start_date: date
    end_date: date
    reason: str | None = None

class LeaveResponse(BaseModel):
    id: int
    employee_id: str
    start_date: date
    end_date: date
    reason: str | None
    status: str


    class Config:
        from_attributes = True

