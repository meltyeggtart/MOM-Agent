"""Review endpoints for a MOM: store, edit, approve, and reopen as a new version.

Approval locks the current version. Editing an approved MOM is not allowed; the
caller reopens it, which writes a new draft version and leaves the approved one
untouched, so the version trail stays honest.
"""

import uuid
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.models import Meeting, Mom, MomStatus, MomVersion
from app.db.session import get_session
from app.schemas.mom import Audience, MomDocument

router = APIRouter(prefix="/meetings/{meeting_id}/moms", tags=["moms"])


class MomVersionRead(BaseModel):
    version_number: int
    content: MomDocument
    ai_generated: bool
    approved_at: datetime | None
    approved_by: str | None
    created_at: datetime

    @classmethod
    def of(cls, version: MomVersion) -> "MomVersionRead":
        return cls(
            version_number=version.version_number,
            content=MomDocument.model_validate(version.content),
            ai_generated=version.ai_generated,
            approved_at=version.approved_at,
            approved_by=version.approved_by,
            created_at=version.created_at,
        )


class MomRead(BaseModel):
    audience: Audience
    status: str
    versions: list[MomVersionRead]

    @classmethod
    def of(cls, mom: Mom) -> "MomRead":
        return cls(
            audience=Audience(mom.audience),
            status=mom.status,
            versions=[
                MomVersionRead.of(version)
                for version in sorted(mom.versions, key=lambda v: v.version_number)
            ],
        )


class ApproveRequest(BaseModel):
    approved_by: str | None = None


SessionDep = Annotated[Session, Depends(get_session)]


def _meeting(session: Session, meeting_id: uuid.UUID) -> Meeting:
    meeting = session.get(Meeting, meeting_id)
    if meeting is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Meeting not found"
        )
    return meeting


def _mom(session: Session, meeting_id: uuid.UUID, audience: Audience) -> Mom:
    _meeting(session, meeting_id)
    mom = (
        session.query(Mom)
        .filter(Mom.meeting_id == meeting_id, Mom.audience == audience.value)
        .one_or_none()
    )
    if mom is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="MOM not found")
    return mom


def _check_audience(document: MomDocument, audience: Audience) -> None:
    if document.audience is not audience:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Document audience {document.audience} does not match {audience}",
        )


def _current(mom: Mom) -> MomVersion:
    return max(mom.versions, key=lambda version: version.version_number)


@router.post(
    "/{audience}/versions",
    response_model=MomRead,
    status_code=status.HTTP_201_CREATED,
)
def store_version(
    meeting_id: uuid.UUID,
    audience: Audience,
    document: MomDocument,
    session: SessionDep,
) -> MomRead:
    """Store a freshly generated MOM as the first draft."""
    _meeting(session, meeting_id)
    _check_audience(document, audience)

    existing = (
        session.query(Mom)
        .filter(Mom.meeting_id == meeting_id, Mom.audience == audience.value)
        .one_or_none()
    )
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This meeting already has a MOM for that audience",
        )

    mom = Mom(meeting_id=meeting_id, audience=audience.value, status=MomStatus.draft)
    mom.versions.append(
        MomVersion(
            version_number=1,
            content=document.model_dump(mode="json"),
            ai_generated=True,
        )
    )
    session.add(mom)
    session.commit()
    session.refresh(mom)
    return MomRead.of(mom)


@router.get("/{audience}", response_model=MomRead)
def read_mom(
    meeting_id: uuid.UUID, audience: Audience, session: SessionDep
) -> MomRead:
    return MomRead.of(_mom(session, meeting_id, audience))


@router.put("/{audience}/draft", response_model=MomRead)
def update_draft(
    meeting_id: uuid.UUID,
    audience: Audience,
    document: MomDocument,
    session: SessionDep,
) -> MomRead:
    _check_audience(document, audience)
    mom = _mom(session, meeting_id, audience)
    if mom.status != MomStatus.draft:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The MOM is approved and locked; reopen it to edit",
        )

    current = _current(mom)
    current.content = document.model_dump(mode="json")
    # An edited draft is no longer exactly what the model wrote.
    current.ai_generated = False
    session.commit()
    session.refresh(mom)
    return MomRead.of(mom)


@router.post("/{audience}/approve", response_model=MomRead)
def approve(
    meeting_id: uuid.UUID,
    audience: Audience,
    session: SessionDep,
    payload: ApproveRequest | None = None,
) -> MomRead:
    mom = _mom(session, meeting_id, audience)
    if mom.status != MomStatus.draft:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="The MOM is already approved"
        )

    current = _current(mom)
    current.approved_at = datetime.now(UTC)
    current.approved_by = payload.approved_by if payload else None
    mom.status = MomStatus.approved
    session.commit()
    session.refresh(mom)
    return MomRead.of(mom)


@router.post("/{audience}/reopen", response_model=MomRead)
def reopen(
    meeting_id: uuid.UUID, audience: Audience, session: SessionDep
) -> MomRead:
    """Start a new draft from the approved version, leaving that version intact."""
    mom = _mom(session, meeting_id, audience)
    if mom.status != MomStatus.approved:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only an approved MOM can be reopened",
        )

    current = _current(mom)
    mom.versions.append(
        MomVersion(
            version_number=current.version_number + 1,
            content=dict(current.content),
            ai_generated=False,
        )
    )
    mom.status = MomStatus.draft
    session.commit()
    session.refresh(mom)
    return MomRead.of(mom)
