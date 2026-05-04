from fastapi import FastAPI
from db.database import engine, Base
from models.leave import LeaveRequest
from models.ticket import Ticket
from models.asset_request import AssetRequest

from app.routes import leave  # import routes
from app.routes import chat

app = FastAPI()

# Create tables

Base.metadata.create_all(bind=engine)

# Include routes

app.include_router(leave.router)
app.include_router(chat.router)
