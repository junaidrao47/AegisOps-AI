from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class LogFinding(Base):
    __tablename__ = "log_findings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    incident_id: Mapped[int] = mapped_column(Integer, ForeignKey("incidents.id"), index=True)
    attachment_id: Mapped[int] = mapped_column(Integer, ForeignKey("incident_attachments.id"), index=True)
    job_id: Mapped[int] = mapped_column(Integer, ForeignKey("log_ingestion_jobs.id"), index=True)

    category: Mapped[str] = mapped_column(String(64), index=True)
    severity: Mapped[str] = mapped_column(String(16), default="medium")  # low|medium|high
    title: Mapped[str] = mapped_column(String(255))
    evidence: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
