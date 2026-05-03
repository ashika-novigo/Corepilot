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

router = APIRouter()



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
def chat(req: ChatRequest,db:Session=Depends(get_db)):

    agent_type = route_query(req.message)
    print("ROUTED TO:", agent_type)

    if agent_type == "hr": 
        reply = hr_agent(req.message, db)
        return {"reply": reply}
   

    
        
    llm = get_llm()
    response = llm.invoke(req.message)

    return {"reply": response.content}

