from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.models.attachment import IncidentAttachment
from app.db.models.event import IncidentEvent
from app.db.models.incident import Incident
from app.db.models.user import User
from app.db.session import get_db
from app.schemas.incidents import AttachmentRead, EventRead, IncidentCreate, IncidentRead
from app.services.storage import read_text_file, save_upload
from app.services.timeline import generate_timeline_from_text

router = APIRouter()


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _get_incident_or_404(db: Session, incident_id: int, owner_user_id: int) -> Incident:
    incident = db.get(Incident, incident_id)
    if not incident or incident.owner_user_id != owner_user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="incident_not_found")
    return incident


@router.post("/incidents", response_model=IncidentRead, status_code=status.HTTP_201_CREATED)
def create_incident(
    payload: IncidentCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Incident:
    incident = Incident(
        owner_user_id=user.id,
        title=payload.title,
        description=payload.description,
        severity=payload.severity,
        environment=payload.environment,
        service_name=payload.service_name,
        deployment_version=payload.deployment_version,
        started_at=payload.started_at,
        ended_at=payload.ended_at,
    )
    db.add(incident)
    db.commit()
    db.refresh(incident)
    return incident


@router.get("/incidents", response_model=list[IncidentRead])
def list_incidents(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[Incident]:
    return (
        db.execute(select(Incident).where(Incident.owner_user_id == user.id).order_by(Incident.created_at.desc()))
        .scalars()
        .all()
    )


@router.get("/incidents/{incident_id}", response_model=IncidentRead)
def get_incident(
    incident_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Incident:
    return _get_incident_or_404(db, incident_id, user.id)


@router.post("/incidents/{incident_id}/attachments", response_model=AttachmentRead)
def upload_incident_attachment(
    incident_id: int,
    kind: str = Form(..., description="log | screenshot | yaml"),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> IncidentAttachment:
    incident = _get_incident_or_404(db, incident_id, user.id)

    kind_normalized = kind.strip().lower()
    if kind_normalized not in {"log", "screenshot", "yaml"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="invalid_attachment_kind")

    # Basic content-type check (best-effort)
    if kind_normalized == "screenshot" and (file.content_type or "").lower() not in {
        "image/png",
        "image/jpeg",
        "image/jpg",
        "image/webp",
    }:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="invalid_screenshot_type")

    if kind_normalized == "yaml" and (file.content_type or "").lower() not in {
        "application/x-yaml",
        "text/yaml",
        "text/plain",
        "application/octet-stream",
    }:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="invalid_yaml_type")

    storage_path, size_bytes = save_upload(user_id=user.id, incident_id=incident.id, kind=kind_normalized, upload=file)

    attachment = IncidentAttachment(
        incident_id=incident.id,
        uploaded_by_user_id=user.id,
        kind=kind_normalized,
        filename=file.filename or "file",
        content_type=file.content_type,
        storage_path=storage_path,
        size_bytes=size_bytes,
    )
    db.add(attachment)

    # Smart feature: auto-generate timeline events from logs (cheap heuristics)
    if kind_normalized == "log":
        try:
            text = read_text_file(storage_path)
            base_date = incident.started_at or incident.created_at
            events = generate_timeline_from_text(text, base_date=base_date)
            for e in events:
                db.add(
                    IncidentEvent(
                        incident_id=incident.id,
                        occurred_at=e.occurred_at,
                        title=e.title,
                        detail=e.detail,
                        source=e.source,
                    )
                )
        except Exception:
            # Don't fail upload if heuristics fail
            pass

    incident.updated_at = _utcnow()
    db.commit()
    db.refresh(attachment)
    return attachment


@router.get("/incidents/{incident_id}/timeline", response_model=list[EventRead])
def get_incident_timeline(
    incident_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[IncidentEvent]:
    incident = _get_incident_or_404(db, incident_id, user.id)
    return (
        db.execute(select(IncidentEvent).where(IncidentEvent.incident_id == incident.id).order_by(IncidentEvent.occurred_at))
        .scalars()
        .all()
    )
