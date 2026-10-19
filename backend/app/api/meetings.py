import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.models import Meeting
from app.db.session import get_session
from app.schemas.meeting import MeetingCreate, MeetingRead

router = APIRouter(prefix="/meetings", tags=["meetings"])

SessionDep = Annotated[Session, Depends(get_session)]


@router.post("", response_model=MeetingRead, status_code=status.HTTP_201_CREATED)
def create_meeting(payload: MeetingCreate, session: SessionDep) -> Meeting:
    meeting = Meeting(**payload.model_dump())
    session.add(meeting)
    session.commit()
    session.refresh(meeting)
    return meeting


@router.get("/{meeting_id}", response_model=MeetingRead)
def read_meeting(meeting_id: uuid.UUID, session: SessionDep) -> Meeting:
    meeting = session.get(Meeting, meeting_id)
    if meeting is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Meeting not found"
        )
    return meeting
