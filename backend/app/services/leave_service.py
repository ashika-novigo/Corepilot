from models.leave import LeaveRequest

def apply_leave(db, employee_id, start_date, end_date, reason="Applied via AI"):
    new_leave = LeaveRequest(
    employee_id=employee_id,
    start_date=start_date,
    end_date=end_date,
    reason=reason
    )


    db.add(new_leave)
    db.commit()
    db.refresh(new_leave)

    return new_leave

def get_leave_history(db, employee_id):
    return db.query(LeaveRequest).filter(
    LeaveRequest.employee_id == employee_id
    ).all()
