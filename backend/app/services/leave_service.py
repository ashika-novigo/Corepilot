from datetime import date
from models.employee import Employee
from models.leave import LeaveRequest


TOTAL_LEAVE_BALANCE = 20


def calculate_total_days(start_date: date, end_date: date):
    return (end_date - start_date).days + 1


def apply_leave(
    db,
    employee_id,
    start_date,
    end_date,
    reason="Applied via AI",
    leave_type="casual",
    manager_email=None
):
    total_days = calculate_total_days(start_date, end_date)

    leave = LeaveRequest(
        employee_id=employee_id,
        start_date=start_date,
        end_date=end_date,
        reason=reason,
        leave_type=leave_type,
        total_days=total_days,
        manager_email=manager_email,
        status="pending"
    )

    db.add(leave)
    db.commit()
    db.refresh(leave)

    return leave


def get_leave_history(db, employee_id):
    return db.query(LeaveRequest).filter(
        LeaveRequest.employee_id == employee_id
    ).all()


def get_pending_leaves(db, employee_id):
    return db.query(LeaveRequest).filter(
        LeaveRequest.employee_id == employee_id,
        LeaveRequest.status == "pending"
    ).all()


def get_leave_balance(db, employee_id):
    approved_leaves = db.query(LeaveRequest).filter(
        LeaveRequest.employee_id == employee_id,
        LeaveRequest.status == "approved"
    ).all()

    used_days = sum(leave.total_days for leave in approved_leaves)

    return {
        "total": TOTAL_LEAVE_BALANCE,
        "used": used_days,
        "remaining": TOTAL_LEAVE_BALANCE - used_days
    }


def cancel_leave(db, employee_id, leave_id):
    leave = db.query(LeaveRequest).filter(
        LeaveRequest.id == leave_id,
        LeaveRequest.employee_id == employee_id
    ).first()

    if not leave:
        return None

    if leave.status != "pending":
        return "not_allowed"

    leave.status = "cancelled"
    db.commit()
    db.refresh(leave)

    return leave


def update_leave_status(db, leave_id, status):
    allowed_status = ["pending", "approved", "rejected", "cancelled"]

    if status not in allowed_status:
        return "invalid_status"

    leave = db.query(LeaveRequest).filter(
        LeaveRequest.id == leave_id
    ).first()

    if not leave:
        return None

    leave.status = status
    db.commit()
    db.refresh(leave)

    return leave

def get_leave_status(db, employee_id, leave_id):
    leave = db.query(LeaveRequest).filter(
        LeaveRequest.id == leave_id,
        LeaveRequest.employee_id == employee_id
    ).first()

    if not leave:
        return None

    return leave

def get_pending_leaves_for_manager(db, manager_id):
    return db.query(LeaveRequest).join(
        Employee,
        LeaveRequest.employee_id == Employee.id
    ).filter(
        Employee.manager_id == manager_id,
        LeaveRequest.status == "pending"
    ).all()


def approve_leave_by_manager(db, leave_id, manager_id):
    leave = db.query(LeaveRequest).join(
        Employee,
        LeaveRequest.employee_id == Employee.id
    ).filter(
        LeaveRequest.id == leave_id,
        Employee.manager_id == manager_id,
        LeaveRequest.status == "pending"
    ).first()

    if not leave:
        return None

    leave.status = "approved"
    db.commit()
    db.refresh(leave)

    return leave


def reject_leave_by_manager(db, leave_id, manager_id):
    leave = db.query(LeaveRequest).join(
        Employee,
        LeaveRequest.employee_id == Employee.id
    ).filter(
        LeaveRequest.id == leave_id,
        Employee.manager_id == manager_id,
        LeaveRequest.status == "pending"
    ).first()

    if not leave:
        return None

    leave.status = "rejected"
    db.commit()
    db.refresh(leave)

    return leave