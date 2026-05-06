from datetime import date
from models.employee import Employee
from models.leave import LeaveRequest
from models.leave_balance import LeaveBalance


LEAVE_TYPES = ("sick", "casual", "earned")


def calculate_total_days(start_date: date, end_date: date):
    return (end_date - start_date).days + 1


def _normalize_leave_type(leave_type: str | None) -> str:
    leave_type = (leave_type or "casual").lower()
    return leave_type if leave_type in LEAVE_TYPES else "casual"


def get_or_create_leave_balance(db, employee_id: int):
    balance = db.query(LeaveBalance).filter(
        LeaveBalance.employee_id == employee_id
    ).first()

    if balance:
        return balance

    balance = LeaveBalance(employee_id=employee_id)
    db.add(balance)
    db.commit()
    db.refresh(balance)
    return balance


def _type_balance(balance, leave_type: str):
    total = getattr(balance, f"{leave_type}_total")
    used = getattr(balance, f"{leave_type}_used")
    return {
        "total": total,
        "used": used,
        "remaining": total - used,
    }


def _insufficient_balance(leave_type: str, remaining: int):
    return {
        "status": "insufficient_balance",
        "leave_type": leave_type,
        "remaining": remaining,
    }


def apply_leave(
    db,
    employee_id,
    start_date,
    end_date,
    reason="Applied via AI",
    leave_type="casual",
    manager_email=None
):
    leave_type = _normalize_leave_type(leave_type)
    total_days = calculate_total_days(start_date, end_date)
    balance = get_or_create_leave_balance(db, employee_id)
    type_balance = _type_balance(balance, leave_type)

    if total_days > type_balance["remaining"]:
        return _insufficient_balance(leave_type, type_balance["remaining"])

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
    balance = get_or_create_leave_balance(db, employee_id)
    return {
        leave_type: _type_balance(balance, leave_type)
        for leave_type in LEAVE_TYPES
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

    if status == "approved" and leave.status == "pending":
        leave_type = _normalize_leave_type(leave.leave_type)
        balance = get_or_create_leave_balance(db, leave.employee_id)
        type_balance = _type_balance(balance, leave_type)

        if leave.total_days > type_balance["remaining"]:
            return _insufficient_balance(leave_type, type_balance["remaining"])

        setattr(
            balance,
            f"{leave_type}_used",
            getattr(balance, f"{leave_type}_used") + leave.total_days,
        )

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
    manager = db.query(Employee).filter(Employee.id == manager_id).first()
    query = db.query(LeaveRequest).join(
        Employee,
        LeaveRequest.employee_id == Employee.id
    ).filter(LeaveRequest.status == "pending")

    if manager and manager.role == "admin":
        return query.all()

    return query.filter(Employee.manager_id == manager_id).all()


def approve_leave_by_manager(db, leave_id, manager_id):
    manager = db.query(Employee).filter(Employee.id == manager_id).first()
    query = db.query(LeaveRequest).join(
        Employee,
        LeaveRequest.employee_id == Employee.id
    ).filter(
        LeaveRequest.id == leave_id,
        LeaveRequest.status == "pending"
    )

    if not (manager and manager.role == "admin"):
        query = query.filter(Employee.manager_id == manager_id)

    leave = query.first()

    if not leave:
        return None

    leave_type = _normalize_leave_type(leave.leave_type)
    balance = get_or_create_leave_balance(db, leave.employee_id)
    type_balance = _type_balance(balance, leave_type)

    if leave.total_days > type_balance["remaining"]:
        return _insufficient_balance(leave_type, type_balance["remaining"])

    setattr(
        balance,
        f"{leave_type}_used",
        getattr(balance, f"{leave_type}_used") + leave.total_days,
    )
    leave.status = "approved"
    db.commit()
    db.refresh(leave)

    return leave


def reject_leave_by_manager(db, leave_id, manager_id):
    manager = db.query(Employee).filter(Employee.id == manager_id).first()
    query = db.query(LeaveRequest).join(
        Employee,
        LeaveRequest.employee_id == Employee.id
    ).filter(
        LeaveRequest.id == leave_id,
        LeaveRequest.status == "pending"
    )

    if not (manager and manager.role == "admin"):
        query = query.filter(Employee.manager_id == manager_id)

    leave = query.first()

    if not leave:
        return None

    leave.status = "rejected"
    db.commit()
    db.refresh(leave)

    return leave
