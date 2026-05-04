from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy.orm import Session
from fastapi import Depends
from db.database import SessionLocal
from models.leave import LeaveRequest
from datetime import date

from ai.groq_client import get_llm
from app.services.ai_service import extract_intent_and_entities

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

# Request schema
class ChatRequest(BaseModel):
    message: str

# Response schema

class ChatResponse(BaseModel):
    reply: str

@router.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest, db: Session = Depends(get_db)):


    result = graph.invoke({
        "message": req.message,
        "db": db
    })

    # If HR handled it
    if "response" in result:
        return {"reply": result["response"]}

    # Otherwise fallback to LLM
    llm = get_llm()
    response = llm.invoke(req.message)

    return {"reply": response.content}


        
    llm = get_llm()
    response = llm.invoke(req.message)

    return {"reply": response.content}

