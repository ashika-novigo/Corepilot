from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from db.database import SessionLocal
from models.leave import LeaveRequest
from models.ticket import Ticket
from models.asset_request import AssetRequest
from models.inventory import Inventory
from models.employee import Employee
from app.services.log_service import get_logs

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])
admin_router = APIRouter(prefix="/admin", tags=["Admin"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _leave_row(db: Session, leave: LeaveRequest):
    employee = db.query(Employee).filter(Employee.id == leave.employee_id).first()
    return {
        "id": leave.id,
        "emp": getattr(employee, "name", str(leave.employee_id)),
        "employee_id": leave.employee_id,
        "type": leave.leave_type,
        "from": str(leave.start_date),
        "to": str(leave.end_date),
        "days": leave.total_days,
        "reason": leave.reason,
        "status": leave.status,
    }


@router.get("/summary")
def dashboard_summary(role: str, email: str, db: Session = Depends(get_db)):
    user = db.query(Employee).filter(Employee.email == email).first()
    role = (role or "").lower()

    leave_query = db.query(LeaveRequest)
    ticket_query = db.query(Ticket)
    asset_query = db.query(AssetRequest)

    if role == "employee" and user:
        leave_query = leave_query.filter(LeaveRequest.employee_id == user.id)
        ticket_query = ticket_query.filter(Ticket.user_id == user.email)
        asset_query = asset_query.filter(AssetRequest.user_id == user.email)
    elif role == "manager" and user:
        team_emails = [e.email for e in db.query(Employee).filter(Employee.manager_id == user.id).all()]
        team_ids = [e.id for e in db.query(Employee).filter(Employee.manager_id == user.id).all()]
        leave_query = leave_query.filter(LeaveRequest.employee_id.in_(team_ids))
        ticket_query = ticket_query.filter(Ticket.user_id.in_(team_emails))
        asset_query = asset_query.filter(AssetRequest.user_id.in_(team_emails))

    pending_leaves = leave_query.filter(LeaveRequest.status == "pending").count()
    open_tickets = ticket_query.filter(Ticket.status.in_(["open", "in_progress"])).count()
    pending_assets = asset_query.filter(
        AssetRequest.final_status.in_(["pending", "pending_it_approval"])
    ).count()

    data = {
        "pending_leaves": pending_leaves,
        "open_tickets": open_tickets,
        "pending_assets": pending_assets,
        "inventory_items": db.query(Inventory).count() if role in ["it", "admin"] else 0,
    }

    if role == "admin":
        data.update({
            "leaves": db.query(LeaveRequest).count(),
            "tickets": db.query(Ticket).count(),
            "assets": db.query(AssetRequest).count(),
            "logs": len(get_logs(db)),
        })

    return data

@router.get("/leaves")
def dashboard_leaves(email: str, role: str, db: Session = Depends(get_db)):
    role = (role or "").lower()
    query = db.query(LeaveRequest)
    user = db.query(Employee).filter(
        Employee.email == email
    ).first()

    if role == "employee" and user:
        query = query.filter(LeaveRequest.employee_id == user.id)
    elif role == "manager" and user:
        team_ids = [e.id for e in db.query(Employee).filter(Employee.manager_id == user.id).all()]
        query = query.filter(LeaveRequest.employee_id.in_(team_ids))

    leaves = query.all()

    return [_leave_row(db, l) for l in leaves]


@router.get("/tickets")
def dashboard_tickets(email: str, role: str, db: Session = Depends(get_db)):
    role = (role or "").lower()
    query = db.query(Ticket)
    user = db.query(Employee).filter(
        Employee.email == email
    ).first()

    if role == "employee" and user:
        query = query.filter(Ticket.user_id == user.email)
    elif role == "manager" and user:
        team_emails = [e.email for e in db.query(Employee).filter(Employee.manager_id == user.id).all()]
        query = query.filter(Ticket.user_id.in_(team_emails))

    tickets = query.all()

    return [
        {
            "id": t.id,
            "emp": t.user_id,
            "title": t.description,
            "priority": t.priority,
            "status": t.status,
            "assignee": getattr(t, "assigned_to", None) or "—",
            "created": str(t.created_at) if getattr(t, "created_at", None) else ""
        }
        for t in tickets
    ]

@router.get("/assets")
def dashboard_assets(email: str, role: str, db: Session = Depends(get_db)):
    role = (role or "").lower()
    query = db.query(AssetRequest)
    user = db.query(Employee).filter(
        Employee.email == email
    ).first()

    if role == "employee" and user:
        query = query.filter(AssetRequest.user_id == user.email)
    elif role == "manager" and user:
        team_emails = [e.email for e in db.query(Employee).filter(Employee.manager_id == user.id).all()]
        query = query.filter(AssetRequest.user_id.in_(team_emails))

    assets = query.all()

    return [
        {
            "id": a.id,
            "emp": a.user_id,
            "asset": a.asset_type,
            "reason": a.reason,
            "manager_status": a.manager_status,
            "it_status": a.it_status,
            "inventory_status": a.inventory_status,
            "final_status": a.final_status,
            "status": a.final_status,
            "created": str(a.created_at) if getattr(a, "created_at", None) else ""
        }
        for a in assets
    ]


@router.get("/inventory")
def dashboard_inventory(email: str = "", role: str = "", db: Session = Depends(get_db)):
    role = (role or "").lower()
    if role not in ["it", "admin"]:
        return []

    items = db.query(Inventory).all()

    return [
        {
            "id": i.id,
            "item": i.asset_type,
            "total": i.total_quantity,
            "available": i.available_quantity,
            "reserved": i.total_quantity - i.available_quantity
        }
        for i in items
    ]


def _log_rows(email: str, role: str, db: Session):
    role = (role or "").lower()
    if role != "admin":
        return {"detail": "Access denied. Only admin can view logs."}

    return [
        {
            "id": log.id,
            "time": str(log.created_at) if log.created_at else "",
            "agent": log.agent,
            "action": log.action,
            "user": log.user_email,
            "status": log.status,
        }
        for log in get_logs(db)
    ]


@router.get("/approvals")
def dashboard_approvals(email: str, role: str, db: Session = Depends(get_db)):
    role = (role or "").lower()
    user = db.query(Employee).filter(Employee.email == email).first()

    leave_query = db.query(LeaveRequest).filter(LeaveRequest.status == "pending")
    manager_asset_query = db.query(AssetRequest).filter(AssetRequest.manager_status == "pending")

    if role == "manager" and user:
        team = db.query(Employee).filter(Employee.manager_id == user.id).all()
        team_ids = [e.id for e in team]
        team_emails = [e.email for e in team]
        leave_query = leave_query.filter(LeaveRequest.employee_id.in_(team_ids))
        manager_asset_query = manager_asset_query.filter(AssetRequest.user_id.in_(team_emails))
    elif role not in ["admin", "hr"]:
        leave_query = leave_query.filter(False)
        manager_asset_query = manager_asset_query.filter(False)

    it_assets = db.query(AssetRequest).filter(
        AssetRequest.manager_status == "approved",
        AssetRequest.it_status == "pending",
    )
    open_tickets = db.query(Ticket).filter(Ticket.status.in_(["open", "in_progress"]))

    if role not in ["it", "admin"]:
        it_assets = it_assets.filter(False)
        open_tickets = open_tickets.filter(False)

    return {
        "leave_approvals": [_leave_row(db, leave) for leave in leave_query.all()]
            if role in ["manager", "hr", "admin"] else [],
        "asset_manager_approvals": [
            {
                "id": a.id,
                "emp": a.user_id,
                "asset": a.asset_type,
                "reason": a.reason,
                "manager_status": a.manager_status,
                "it_status": a.it_status,
                "inventory_status": a.inventory_status,
                "final_status": a.final_status,
                "status": a.final_status,
                "created": str(a.created_at) if a.created_at else "",
            }
            for a in manager_asset_query.all()
        ],
        "asset_it_approvals": [
            {
                "id": a.id,
                "emp": a.user_id,
                "asset": a.asset_type,
                "reason": a.reason,
                "manager_status": a.manager_status,
                "it_status": a.it_status,
                "inventory_status": a.inventory_status,
                "final_status": a.final_status,
                "status": a.final_status,
                "created": str(a.created_at) if a.created_at else "",
            }
            for a in it_assets.all()
        ],
        "open_tickets": [
            {
                "id": t.id,
                "emp": t.user_id,
                "title": t.description,
                "priority": t.priority,
                "status": t.status,
                "assignee": getattr(t, "assigned_to", None) or "—",
                "created": str(t.created_at) if t.created_at else "",
            }
            for t in open_tickets.all()
        ],
    }


@router.get("/logs")
def dashboard_logs(email: str, role: str, db: Session = Depends(get_db)):
    return _log_rows(email, role, db)


@router.get("/employees")
def dashboard_employees(email: str, role: str, db: Session = Depends(get_db)):
    if role != "admin":
        return {"detail": "Access denied. Only admin can view all employees."}

    employees = db.query(Employee).all()
    return [
        {
            "id": e.id,
            "name": e.name,
            "email": e.email,
            "role": e.role,
            "department": e.department,
            "manager_id": e.manager_id,
            "created_at": str(e.created_at) if e.created_at else "",
        }
        for e in employees
    ]


@admin_router.get("/logs")
def admin_logs(email: str, role: str, db: Session = Depends(get_db)):
    return _log_rows(email, role, db)


