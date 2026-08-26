from sqlalchemy import Column, DateTime, Integer, String, Text, UniqueConstraint, func

from app.core.database import Base


class PipelineRun(Base):
    __tablename__ = "pipeline_runs"
    __table_args__ = (
        UniqueConstraint("pipeline_name", "run_id", name="uq_pipeline_runs_pipeline_run"),
    )

    id = Column(Integer, primary_key=True, index=True)
    pipeline_name = Column(String(100), nullable=False, index=True)
    run_id = Column(String(255), nullable=False, index=True)
    source_system = Column(String(255), nullable=True, index=True)
    batch_id = Column(String(255), nullable=True, index=True)
    status = Column(String(50), nullable=False, default="processing", server_default="processing", index=True)
    started_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), index=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    duration_ms = Column(Integer, nullable=True)
    received_count = Column(Integer, nullable=False, default=0, server_default="0")
    accepted_count = Column(Integer, nullable=False, default=0, server_default="0")
    rejected_count = Column(Integer, nullable=False, default=0, server_default="0")
    duplicate_or_updated_count = Column(Integer, nullable=False, default=0, server_default="0")
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
