from sqlalchemy import Column, Integer, String, DateTime
from datetime import datetime, timezone
from db.database import Base


class AssetRequest(Base):
    __tablename__ = "asset_requests"

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(String, nullable=False)

    asset_type = Column(String, nullable=False)
    reason = Column(String, nullable=True)

    manager_status = Column(String, nullable=False, default="pending")
    it_status = Column(String, nullable=False, default="pending")
    inventory_status = Column(String, nullable=False, default="pending")

    final_status = Column(String, nullable=False, default="pending")

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )