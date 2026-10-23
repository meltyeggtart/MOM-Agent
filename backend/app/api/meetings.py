import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.auth import CurrentUser
from app.db.models import Meeting
from app.db.session import get_session
from app.schemas.meeting import MeetingCreate, MeetingRead

router = APIRouter(prefix="/meetings", tags=["meetings"])

SessionDep = Annotated[Session, Depends(get_session)]


def load_meeting(
    session: Session, meeting_id: uuid.UUID, owner_id: uuid.UUID
) -> Meeting:
    """One owner's meeting.

    Another owner's id is reported as missing rather than forbidden, so the response
    cannot be used to learn that a meeting exists.
    """
    meeting = (
        session.query(Meeting)
        .filter(Meeting.id == meeting_id, Meeting.owner_id == owner_id)
        .one_or_none()
    )
    if meeting is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Meeting not found"
        )
    return meeting


@router.post("", response_model=MeetingRead, status_code=status.HTTP_201_CREATED)
def create_meeting(
    payload: MeetingCreate, session: SessionDep, user: CurrentUser
) -> Meeting:
    meeting = Meeting(**payload.model_dump(), owner_id=user.id)
    session.add(meeting)
    session.commit()
    session.refresh(meeting)
    return meeting


@router.get("/{meeting_id}", response_model=MeetingRead)
def read_meeting(
    meeting_id: uuid.UUID, session: SessionDep, user: CurrentUser
) -> Meeting:
    return load_meeting(session, meeting_id, user.id)
