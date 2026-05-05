from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy.orm import Session
from fastapi import Depends
from db.database import SessionLocal
from models.leave import LeaveRequest
from datetime import date
from models.employee import Employee
from app.services.auth_services import verify_password, create_access_token
from ai.groq_client import get_llm
from app.services.ai_service import extract_intent_and_entities
from app.services.auth_services import decode_access_token

from ai.agents.router_agent import route_query
from ai.agents.hr_agent import hr_agent
from ai.graph import build_graph

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

@router.post("/login", response_model=LoginResponse)
def login(req: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(Employee).filter(Employee.email == req.email).first()

    if not user:
        return {
            "success": False,
            "message": "User not found"
        }

    if not verify_password(req.password, user.password_hash):
        return {
            "success": False,
            "message": "Invalid password"
        }

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
        "role": user.role
    }



@router.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest, db: Session = Depends(get_db)):

    payload = decode_access_token(req.token)

    if not payload:
        return {
            "reply": "Invalid or expired token. Please login again.",
            "agent": "auth"
        }

    user = db.query(Employee).filter(
        Employee.email == payload.get("email")
    ).first()

    if not user:
        return {
            "reply": "User not found.",
            "agent": "auth"
        }

    result = graph.invoke({
    "message": req.message,
    "db": db,
    "user": user
        })

    # If HR handled it
    if "response" in result:
        return {"reply": result["response"],
                "agent": result.get("agent", "general") 
                } # 👈 ADD THIS

    # Otherwise fallback to LLM
    llm = get_llm()
    response = llm.invoke(req.message)

    return {"reply": response.content, "agent": "general"}


  

