import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class RecordingRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    meeting_id: uuid.UUID
    content_type: str
    byte_size: int
    duration_ms: int | None
    uploaded_at: datetime
    expires_at: datetime | None
