from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class LogChunk(Base):
    __tablename__ = "log_chunks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    incident_id: Mapped[int] = mapped_column(Integer, ForeignKey("incidents.id"), index=True)
    attachment_id: Mapped[int] = mapped_column(Integer, ForeignKey("incident_attachments.id"), index=True)
    job_id: Mapped[int] = mapped_column(Integer, ForeignKey("log_ingestion_jobs.id"), index=True)

    chunk_index: Mapped[int] = mapped_column(Integer, index=True)
    text: Mapped[str] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
