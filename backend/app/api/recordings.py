import uuid
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api.auth import CurrentUser
from app.api.meetings import load_meeting
from app.core.settings import settings
from app.db.models import Meeting, Recording
from app.db.session import get_session
from app.schemas.recording import RecordingRead
from app.services.storage import LocalAudioStorage, get_audio_storage

router = APIRouter(tags=["recordings"])

SessionDep = Annotated[Session, Depends(get_session)]
StorageDep = Annotated[LocalAudioStorage, Depends(get_audio_storage)]

CHUNK_BYTES = 1024 * 1024
MAX_UPLOAD_BYTES = 200 * 1024 * 1024

# Browsers send the codec as a parameter, for example "audio/webm;codecs=opus".
SUFFIX_BY_CONTENT_TYPE = {
    "audio/webm": ".webm",
    "audio/ogg": ".ogg",
    "audio/mp4": ".m4a",
    "audio/mpeg": ".mp3",
    "audio/wav": ".wav",
    "audio/x-wav": ".wav",
}


def _chunks(file: UploadFile) -> Iterator[bytes]:
    received = 0
    while chunk := file.file.read(CHUNK_BYTES):
        received += len(chunk)
        if received > MAX_UPLOAD_BYTES:
            raise HTTPException(
                status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                detail="Recording is larger than 200 MB",
            )
        yield chunk


@router.post(
    "/meetings/{meeting_id}/recordings",
    response_model=RecordingRead,
    status_code=status.HTTP_201_CREATED,
)
def upload_recording(
    meeting_id: uuid.UUID,
    file: Annotated[UploadFile, File()],
    session: SessionDep,
    storage: StorageDep,
    user: CurrentUser,
    duration_ms: Annotated[int | None, Form()] = None,
) -> Recording:
    load_meeting(session, meeting_id, user.id)

    content_type = (file.content_type or "").split(";")[0].strip().lower()
    suffix = SUFFIX_BY_CONTENT_TYPE.get(content_type)
    if suffix is None:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Unsupported audio type",
        )

    # Only the generated key reaches storage, so a client filename cannot escape the
    # storage root.
    key, size = storage.save(_chunks(file), suffix)
    if size == 0:
        storage.delete(key)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Recording is empty"
        )

    recording = Recording(
        meeting_id=meeting_id,
        storage_key=key,
        content_type=content_type,
        byte_size=size,
        duration_ms=duration_ms,
        expires_at=datetime.now(UTC) + timedelta(days=settings.retention_days),
    )
    session.add(recording)
    session.commit()
    session.refresh(recording)
    return recording


@router.get("/recordings/{recording_id}/audio")
def download_recording(
    recording_id: uuid.UUID,
    session: SessionDep,
    storage: StorageDep,
    user: CurrentUser,
) -> FileResponse:
    recording = (
        session.query(Recording)
        .join(Meeting, Meeting.id == Recording.meeting_id)
        .filter(Recording.id == recording_id, Meeting.owner_id == user.id)
        .one_or_none()
    )
    if recording is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Recording not found"
        )
    path = storage.path_for(recording.storage_key)
    if not path.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Audio file not found"
        )
    return FileResponse(path, media_type=recording.content_type)
