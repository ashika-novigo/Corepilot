from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from db.database import SessionLocal
from models.leave_schema import LeaveCreate, LeaveResponse
from app.services.leave_service import (
    apply_leave as apply_leave_service,
    get_leave_history as get_leave_history_service,
    update_leave_status as update_leave_status_service,
)

router = APIRouter()

# DB dependency

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Apply Leave

@router.post("/apply-leave", response_model=LeaveResponse)
def apply_leave(leave: LeaveCreate, db: Session = Depends(get_db)):
    new_leave = apply_leave_service(
        db=db,
        employee_id=leave.employee_id,
        start_date=leave.start_date,
        end_date=leave.end_date,
        reason=leave.reason,
        leave_type=leave.leave_type,
    )

    if isinstance(new_leave, dict) and new_leave.get("status") == "insufficient_balance":
        raise HTTPException(
            status_code=400,
            detail=(
                f"You only have {new_leave['remaining']} {new_leave['leave_type']} "
                "leaves remaining."
            ),
        )

    return new_leave


# Get Leave History

@router.get("/leave-history/{employee_id}", response_model=list[LeaveResponse])
def get_leave_history(employee_id: str, db: Session = Depends(get_db)):
    return get_leave_history_service(db, employee_id)


# Approve / Reject Leave

@router.put("/leave/{leave_id}", response_model=LeaveResponse)
def update_leave_status(leave_id: int,status: str,db: Session = Depends(get_db)):
    if status not in ["approved", "rejected"]:
        raise HTTPException(status_code=400, detail="Invalid status")

    leave = update_leave_status_service(db, leave_id, status)
    if isinstance(leave, dict) and leave.get("status") == "insufficient_balance":
        raise HTTPException(
            status_code=400,
            detail=(
                f"You only have {leave['remaining']} {leave['leave_type']} "
                "leaves remaining."
            ),
        )
    if not leave:
        raise HTTPException(status_code=404, detail="Leave not found")

    return leave

