"""Post-meeting transcription worker.

Run it as its own process: `python -m app.worker`. It polls for recordings whose
meeting has no English transcript yet, transcribes them, and stores the result. The
query is the queue, which keeps this first version free of a queue service.
"""

import argparse
import logging
import time

from sqlalchemy import exists, select
from sqlalchemy.orm import Session

from app.core.settings import settings
from app.db.models import Recording, Transcript
from app.db.session import SessionLocal
from app.services.speech import SpeechToText, get_speech_to_text
from app.services.storage import LocalAudioStorage, get_audio_storage

logger = logging.getLogger(__name__)

LANGUAGE = "en"


def transcribe_pending(
    session: Session,
    *,
    storage: LocalAudioStorage | None = None,
    speech: SpeechToText | None = None,
) -> int:
    storage = storage or get_audio_storage()
    speech = speech or get_speech_to_text()

    has_transcript = exists().where(
        Transcript.meeting_id == Recording.meeting_id,
        Transcript.language == LANGUAGE,
    )
    pending = session.scalars(
        select(Recording.id).where(~has_transcript).order_by(Recording.uploaded_at)
    ).all()

    saved = 0
    for recording_id in pending:
        recording = session.get(Recording, recording_id)
        path = storage.path_for(recording.storage_key)
        if not path.is_file():
            logger.warning("Audio missing for recording %s", recording_id)
            continue

        result = speech.transcribe(path, LANGUAGE)
        session.add(
            Transcript(
                meeting_id=recording.meeting_id,
                language=LANGUAGE,
                text=result.text,
                segments=[
                    {"start_ms": s.start_ms, "end_ms": s.end_ms, "text": s.text}
                    for s in result.segments
                ],
                provider=result.provider,
            )
        )
        session.commit()
        saved += 1
        logger.info(
            "Transcribed recording %s (%d characters)",
            recording_id,
            len(result.text),
        )
    return saved


def main() -> None:
    parser = argparse.ArgumentParser(description="Transcribe recordings")
    parser.add_argument("--once", action="store_true", help="run one pass and exit")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s"
    )
    while True:
        with SessionLocal() as session:
            saved = transcribe_pending(session)
        if args.once:
            return
        if saved == 0:
            time.sleep(settings.worker_poll_seconds)


if __name__ == "__main__":
    main()
