from sqlalchemy import Column, Date, Integer, String

from db.database import Base


class Holiday(Base):
    __tablename__ = "holidays"

    id = Column(Integer, primary_key=True, index=True)
    holiday_date = Column(Date, unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    holiday_type = Column(String(50), nullable=False, default="company")
