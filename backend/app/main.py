from fastapi import FastAPI, Depends
from db.database import engine, Base, SessionLocal
from models.leave import LeaveRequest
from sqlalchemy.orm import Session
from models.leave_schema import LeaveCreate, LeaveResponse

app=FastAPI()

Base.metadata.create_all(bind=engine)

def get_db():
    db=SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.get('/')
def home():
    return {"message":"enterprise copilot backend running"}

@app.post('/apply-leave',response_model=LeaveResponse)
def applyLeave(leave:LeaveCreate, db:Session=Depends(get_db)):
    new_leave=LeaveRequest(
        employee_id=leave.employee_id, 
        start_date=leave.start_date, 
        end_date=leave.end_date,
        reason=leave.reason
    )

    db.add(new_leave)
    db.commit()
    db.refresh(new_leave)

    return new_leave

@app.get('/leave-history/{employee_id}', response_model=list[LeaveResponse])
def leaveHistory(employee_id: str, db:Session=Depends(get_db)):
    leaves = db.query(LeaveRequest).filter(
        LeaveRequest.employee_id == employee_id
    ).all() 
    return leaves   

from fastapi import HTTPException

# Approve / Reject Leave API

@app.put("/leave/{leave_id}", response_model=LeaveResponse)
def update_leave_status(leave_id: int,status: str,db: Session = Depends(get_db)):
    leave = db.query(LeaveRequest).filter(
    LeaveRequest.id == leave_id
    ).first()


    if not leave:
        raise HTTPException(status_code=404, detail="Leave not found")

    if status not in ["approved", "rejected"]:
        raise HTTPException(status_code=400, detail="Invalid status")

    leave.status = status

    db.commit()
    db.refresh(leave)

    return leave

