from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class LogIngestionJob(Base):
    __tablename__ = "log_ingestion_jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    incident_id: Mapped[int] = mapped_column(Integer, ForeignKey("incidents.id"), index=True)
    attachment_id: Mapped[int] = mapped_column(Integer, ForeignKey("incident_attachments.id"), index=True)

    status: Mapped[str] = mapped_column(String(32), default="queued")  # queued|running|succeeded|failed
    source_type: Mapped[str | None] = mapped_column(String(64), nullable=True)

    error: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
