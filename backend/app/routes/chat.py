from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy.orm import Session
from fastapi import Depends
from db.database import SessionLocal
from models.employee import Employee
from models.leave import LeaveRequest
from models.ticket import Ticket
from models.asset_request import AssetRequest
from models.inventory import Inventory
from app.services.auth_services import verify_password, create_access_token
from ai.groq_client import get_llm
from app.services.auth_services import decode_access_token
from app.services.log_service import create_log, get_logs

from ai.agents.hr_agent import hr_agent
from ai.graph import build_graph
from ai.state import agent_state_store

router = APIRouter()
graph = build_graph()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class LoginRequest(BaseModel):
    email: str
    password: str


class LoginResponse(BaseModel):
    success: bool
    token: str | None = None
    name: str | None = None
    email: str | None = None
    role: str | None = None
    message: str | None = None


# Request schema
class ChatRequest(BaseModel):
    message: str
    token: str


# Response schema
class ChatResponse(BaseModel):
    reply: str


def _general_prompt(session_state, message: str) -> str:
    history = session_state.history_text(limit=8)
    return f"""
You are Corepilot, an internal employee assistant.

Use the conversation history for continuity. If the user asks for HR or IT
operations, keep the answer brief and suggest the relevant request clearly.

Conversation history:
{history}

Current message:
{message}
"""


def _is_contextual_follow_up(message: str) -> bool:
    return message.strip().lower() in {
        "show status",
        "status",
        "track status",
        "show history",
        "history",
        "my requests",
        "my status",
    }


def _rows_or_empty(rows: list[str], empty: str) -> str:
    return "\n".join(rows) if rows else empty


def _format_employees(db: Session) -> str:
    employees = db.query(Employee).order_by(Employee.id).all()
    return _rows_or_empty(
        [
            f"Employee #{e.id}: {e.name} | {e.email} | Role: {e.role} | Dept: {e.department or '-'} | Manager: {e.manager_id or '-'}"
            for e in employees
        ],
        "No employees found.",
    )


def _format_leaves(db: Session, pending_only: bool = False) -> str:
    query = db.query(LeaveRequest)
    if pending_only:
        query = query.filter(LeaveRequest.status == "pending")
    leaves = query.order_by(LeaveRequest.id).all()
    return _rows_or_empty(
        [
            f"Leave #{l.id}: Employee {l.employee_id} | {l.leave_type} | {l.start_date} to {l.end_date} | Days: {l.total_days} | Status: {l.status}"
            for l in leaves
        ],
        "No leave requests found.",
    )


def _format_tickets(db: Session, open_only: bool = False) -> str:
    query = db.query(Ticket)
    if open_only:
        query = query.filter(Ticket.status.in_(["open", "in_progress"]))
    tickets = query.order_by(Ticket.id).all()
    return _rows_or_empty(
        [
            f"Ticket #{t.id}: {t.issue_type} | User: {t.user_id} | Priority: {t.priority} | Status: {t.status}"
            for t in tickets
        ],
        "No IT tickets found.",
    )


def _format_assets(db: Session, pending_manager: bool = False, pending_it: bool = False) -> str:
    query = db.query(AssetRequest)
    if pending_manager:
        query = query.filter(AssetRequest.manager_status == "pending")
    if pending_it:
        query = query.filter(
            AssetRequest.manager_status == "approved",
            AssetRequest.it_status == "pending",
        )
    assets = query.order_by(AssetRequest.id).all()
    return _rows_or_empty(
        [
            f"Asset #{a.id}: {a.asset_type} | User: {a.user_id} | Manager: {a.manager_status} | IT: {a.it_status} | Final: {a.final_status}"
            for a in assets
        ],
        "No asset requests found.",
    )


def _format_inventory(db: Session, low_stock: bool = False) -> str:
    query = db.query(Inventory)
    if low_stock:
        query = query.filter(Inventory.available_quantity <= 2)
    items = query.order_by(Inventory.id).all()
    return _rows_or_empty(
        [
            f"Inventory #{i.id}: {i.asset_type} | Total: {i.total_quantity} | Available: {i.available_quantity} | Reserved: {i.total_quantity - i.available_quantity}"
            for i in items
        ],
        "No inventory items found.",
    )


def _format_logs(db: Session, agent_only: bool = False) -> str:
    logs = get_logs(db)[:25]
    if agent_only:
        logs = [log for log in logs if log.agent]
    return _rows_or_empty(
        [
            f"Log #{log.id}: {log.created_at} | {log.user_email} | Agent: {log.agent} | Action: {log.action} | Status: {log.status}"
            for log in logs
        ],
        "No logs found.",
    )


def _format_summary(db: Session) -> str:
    return (
        "Dashboard Summary:\n"
        f"Employees: {db.query(Employee).count()}\n"
        f"Leave requests: {db.query(LeaveRequest).count()}\n"
        f"Pending leaves: {db.query(LeaveRequest).filter(LeaveRequest.status == 'pending').count()}\n"
        f"Tickets: {db.query(Ticket).count()}\n"
        f"Open tickets: {db.query(Ticket).filter(Ticket.status.in_(['open', 'in_progress'])).count()}\n"
        f"Asset requests: {db.query(AssetRequest).count()}\n"
        f"Pending assets: {db.query(AssetRequest).filter(AssetRequest.final_status.in_(['pending', 'pending_it_approval'])).count()}\n"
        f"Inventory items: {db.query(Inventory).count()}\n"
        f"System logs: {len(get_logs(db))}"
    )


def _admin_command_response(message: str, db: Session, user: Employee, session_state) -> str | None:
    msg = message.lower().strip()
    admin_terms = (
        "all employees",
        "employee profiles",
        "employee details",
        "all leave",
        "leave history",
        "leave requests",
        "pending leave",
        "all tickets",
        "ticket status",
        "open tickets",
        "pending tickets",
        "all asset",
        "asset requests",
        "manager asset approvals",
        "it asset approvals",
        "inventory",
        "low stock",
        "system logs",
        "agent activity",
        "dashboard summary",
        "analytics",
    )

    if not any(term in msg for term in admin_terms):
        return None

    if user.role != "admin":
        session_state.metadata["last_action"] = "access_denied"
        session_state.metadata["last_status"] = "access_denied"
        session_state.metadata["last_tool"] = "admin_command"
        return "Access denied. Only admin can use this admin view."

    session_state.set_agent("admin")
    session_state.metadata["last_tool"] = "admin_command"
    session_state.metadata["last_status"] = "success"

    if "employee" in msg:
        session_state.metadata["last_action"] = "admin_view_employees"
        return _format_employees(db)
    if "pending leave" in msg or "pending approvals" in msg:
        session_state.metadata["last_action"] = "admin_view_pending_leaves"
        return _format_leaves(db, pending_only=True)
    if "leave" in msg:
        session_state.metadata["last_action"] = "admin_view_leave_requests"
        return _format_leaves(db)
    if "open tickets" in msg or "pending tickets" in msg or "in-progress" in msg or "in progress" in msg:
        session_state.metadata["last_action"] = "admin_view_open_tickets"
        return _format_tickets(db, open_only=True)
    if "ticket" in msg:
        session_state.metadata["last_action"] = "admin_view_tickets"
        return _format_tickets(db)
    if "low stock" in msg:
        session_state.metadata["last_action"] = "admin_view_low_stock"
        return _format_inventory(db, low_stock=True)
    if "inventory" in msg:
        session_state.metadata["last_action"] = "admin_view_inventory"
        return _format_inventory(db)
    if "it asset approvals" in msg or "pending it" in msg:
        session_state.metadata["last_action"] = "admin_view_it_asset_approvals"
        return _format_assets(db, pending_it=True)
    if "manager asset approvals" in msg or "pending manager" in msg:
        session_state.metadata["last_action"] = "admin_view_manager_asset_approvals"
        return _format_assets(db, pending_manager=True)
    if "asset" in msg:
        session_state.metadata["last_action"] = "admin_view_asset_requests"
        return _format_assets(db)
    if "agent activity" in msg:
        session_state.metadata["last_action"] = "admin_view_agent_logs"
        return _format_logs(db, agent_only=True)
    if "logs" in msg or "traces" in msg:
        session_state.metadata["last_action"] = "admin_view_logs"
        return _format_logs(db)
    if "summary" in msg or "analytics" in msg:
        session_state.metadata["last_action"] = "admin_view_dashboard_summary"
        return _format_summary(db)

    return None


@router.post("/login", response_model=LoginResponse)
def login(req: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(Employee).filter(Employee.email == req.email).first()

    if not user:
        return {"success": False, "message": "User not found"}

    if not verify_password(req.password, user.password_hash):
        return {"success": False, "message": "Invalid password"}

    token = create_access_token({
        "user_id": user.id,
        "email": user.email,
        "role": user.role
    })

    return {
        "success": True,
        "token": token,
        "name": user.name,
        "email": user.email,
        "role": user.role,
    }


@router.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest, db: Session = Depends(get_db)):

    payload = decode_access_token(req.token)

    if not payload:
        return {"reply": "Invalid or expired token. Please login again."}

    user = db.query(Employee).filter(
        Employee.email == payload.get("email")
    ).first()

    if not user:
        return {"reply": "User not found."}

    user_key = str(user.id)
    session_state = agent_state_store.get(user_key)
    history = session_state.history

    if session_state.get_pending("hr_leave"):
        reply = hr_agent(req.message, db, user, history, session_state=session_state)

    elif session_state.get_pending("it_action"):
        from ai.agents.it_agent import it_agent

        reply = it_agent(req.message, db, user, history, session_state=session_state)

    elif (admin_reply := _admin_command_response(req.message, db, user, session_state)) is not None:
        reply = admin_reply

    elif _is_contextual_follow_up(req.message) and session_state.last_agent == "hr":
        reply = hr_agent(req.message, db, user, history, session_state=session_state)

    elif _is_contextual_follow_up(req.message) and session_state.last_agent == "it":
        from ai.agents.it_agent import it_agent

        reply = it_agent(req.message, db, user, history, session_state=session_state)

    else:
        # Let LangGraph route to HR, IT, or the general fallback.
        result = graph.invoke({
            "message": req.message,
            "db": db,
            "user": user,
            "history": history,
            "session_state": session_state,
        })

        if "response" in result and result["response"]:
            reply = result["response"]
            session_state.set_agent(result.get("agent"))
        else:
            llm = get_llm()
            response = llm.invoke(_general_prompt(session_state, req.message))
            reply = response.content
            session_state.set_agent("general")

    session_state.record_exchange(req.message, reply)
    create_log(
        db=db,
        user=user,
        agent=session_state.last_agent,
        action=session_state.metadata.pop("last_action", "chat_response"),
        tool_used=session_state.metadata.pop("last_tool", session_state.last_agent),
        status=session_state.metadata.pop("last_status", "success"),
        message=req.message,
        response=reply,
    )

    return {"reply": reply}
