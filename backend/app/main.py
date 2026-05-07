from fastapi import FastAPI
from db.database import engine, Base
from models.leave import LeaveRequest
from models.ticket import Ticket
from models.asset_request import AssetRequest
from models.leave_balance import LeaveBalance
from models.holiday import Holiday
from models.system_log import SystemLog
from fastapi.middleware.cors import CORSMiddleware
from models.employee import Employee
from app.routes import leave  # import routes
from app.routes import chat
from app.routes import dashboard

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create tables

Base.metadata.create_all(bind=engine)

# Include routes

app.include_router(leave.router)
app.include_router(chat.router)
app.include_router(dashboard.router)
app.include_router(dashboard.admin_router)
