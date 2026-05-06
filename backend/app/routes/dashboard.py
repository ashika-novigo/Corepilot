from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from db.database import SessionLocal
from models.leave import LeaveRequest
from models.ticket import Ticket
from models.asset_request import AssetRequest
from models.inventory import Inventory
from models.employee import Employee

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/summary")
def dashboard_summary(role: str, email: str, db: Session = Depends(get_db)):
    leave_count = db.query(LeaveRequest).filter(
        LeaveRequest.status == "pending"
    ).count()

    ticket_count = db.query(Ticket).filter(
        Ticket.status != "resolved"
    ).count()

    asset_count = db.query(AssetRequest).filter(
        AssetRequest.final_status.in_(["pending", "pending_it_approval"])
    ).count()

    inventory_count = db.query(Inventory).count()

    return {
        "pending_leaves": leave_count,
        "open_tickets": ticket_count,
        "pending_assets": asset_count,
        "inventory_items": inventory_count
    }

@router.get("/leaves")
def dashboard_leaves(email: str, role: str, db: Session = Depends(get_db)):
    query = db.query(LeaveRequest)
    user = db.query(Employee).filter(
        Employee.email == email
    ).first()

    if role == "employee":
        query = query.filter(LeaveRequest.employee_id == user.id)

    leaves = query.all()

    return [
        {
            "id": l.id,
            "employee_id": l.employee_id,
            "type": l.leave_type,
            "from": str(l.start_date),
            "to": str(l.end_date),
            "days": l.total_days,
            "reason": l.reason,
            "status": l.status
        }
        for l in leaves
    ]


@router.get("/tickets")
def dashboard_tickets(email: str, role: str, db: Session = Depends(get_db)):
    query = db.query(Ticket)
    user = db.query(Employee).filter(
        Employee.email == email
    ).first()

    if role == "employee":
        query = query.filter(Ticket.user_id ==user.id)

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
    query = db.query(AssetRequest)
    user = db.query(Employee).filter(
        Employee.email == email
    ).first()

    if role == "employee":
        query = query.filter(AssetRequest.user_id == user.id)

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
            "created": str(a.created_at) if getattr(a, "created_at", None) else ""
        }
        for a in assets
    ]


@router.get("/inventory")
def dashboard_inventory(db: Session = Depends(get_db)):
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


