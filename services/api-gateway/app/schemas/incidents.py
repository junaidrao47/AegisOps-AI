from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class IncidentCreate(BaseModel):
    title: str = Field(min_length=3, max_length=255)
    description: str | None = None

    severity: str = Field(default="medium")
    environment: str = Field(default="production")
    service_name: str | None = None
    deployment_version: str | None = None

    started_at: datetime | None = None
    ended_at: datetime | None = None


class IncidentRead(BaseModel):
    id: int
    title: str
    description: str | None

    severity: str
    environment: str
    service_name: str | None
    deployment_version: str | None

    started_at: datetime | None
    ended_at: datetime | None

    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class AttachmentRead(BaseModel):
    id: int
    incident_id: int
    kind: str
    filename: str
    content_type: str | None
    size_bytes: int
    created_at: datetime

    model_config = {"from_attributes": True}


class EventRead(BaseModel):
    id: int
    incident_id: int
    occurred_at: datetime
    title: str
    detail: str | None
    source: str

    model_config = {"from_attributes": True}
