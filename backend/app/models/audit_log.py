from sqlalchemy import Column, DateTime, ForeignKey, Integer, JSON, String, func

from app.core.database import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    username = Column(String(100), nullable=True, index=True)
    role = Column(String(100), nullable=True)
    action = Column(String(100), nullable=False, index=True)
    resource_type = Column(String(100), nullable=True, index=True)
    resource_id = Column(String(255), nullable=True, index=True)
    patient_id = Column(Integer, nullable=True, index=True)
    event_timestamp = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), index=True)
    event_metadata = Column("metadata", JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
