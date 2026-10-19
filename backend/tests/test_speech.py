from datetime import UTC, datetime
from pathlib import Path

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Meeting, Recording, Transcript
from app.services.speech import WhisperSpeechToText
from app.services.storage import LocalAudioStorage
from app.worker import transcribe_pending

FIXTURE = Path(__file__).parent / "fixtures" / "kickoff.mp3"


@pytest.fixture(scope="session")
def speech() -> WhisperSpeechToText:
    return WhisperSpeechToText()


@pytest.fixture
def stored_audio(tmp_path: Path) -> LocalAudioStorage:
    root = tmp_path / "audio"
    root.mkdir()
    (root / "kickoff.mp3").write_bytes(FIXTURE.read_bytes())
    return LocalAudioStorage(root=root)


def _meeting(session: Session) -> Meeting:
    meeting = Meeting(
        title="Kickoff",
        meeting_at=datetime(2026, 11, 2, 9, 30, tzinfo=UTC),
        languages=["en"],
    )
    session.add(meeting)
    session.commit()
    return meeting


def _recording(
    session: Session, meeting: Meeting, key: str = "kickoff.mp3"
) -> Recording:
    recording = Recording(
        meeting_id=meeting.id,
        storage_key=key,
        content_type="audio/mpeg",
        byte_size=FIXTURE.stat().st_size,
    )
    session.add(recording)
    session.commit()
    return recording


def test_whisper_transcribes_english_speech(speech: WhisperSpeechToText) -> None:
    result = speech.transcribe(FIXTURE, "en")

    text = result.text.lower()
    assert "kickoff" in text
    assert "budget" in text
    assert result.language == "en"
    assert result.provider == "faster-whisper"
    assert result.segments
    assert result.segments[0].start_ms == 0
    assert result.segments[-1].end_ms > 0


def test_worker_saves_a_transcript(
    db_session: Session, stored_audio: LocalAudioStorage, speech: WhisperSpeechToText
) -> None:
    meeting = _meeting(db_session)
    _recording(db_session, meeting)

    saved = transcribe_pending(db_session, storage=stored_audio, speech=speech)

    assert saved == 1
    transcript = db_session.scalars(select(Transcript)).one()
    assert transcript.meeting_id == meeting.id
    assert transcript.language == "en"
    assert "kickoff" in transcript.text.lower()
    assert transcript.provider == "faster-whisper"
    assert transcript.segments[0]["text"]
    assert transcript.segments[-1]["end_ms"] > 0


def test_worker_does_not_transcribe_the_same_meeting_twice(
    db_session: Session, stored_audio: LocalAudioStorage, speech: WhisperSpeechToText
) -> None:
    meeting = _meeting(db_session)
    _recording(db_session, meeting)
    transcribe_pending(db_session, storage=stored_audio, speech=speech)

    saved = transcribe_pending(db_session, storage=stored_audio, speech=speech)

    assert saved == 0
    assert len(db_session.scalars(select(Transcript)).all()) == 1


def test_worker_skips_a_recording_whose_audio_is_missing(
    db_session: Session, tmp_path: Path, speech: WhisperSpeechToText
) -> None:
    meeting = _meeting(db_session)
    _recording(db_session, meeting, key="gone.mp3")

    saved = transcribe_pending(
        db_session, storage=LocalAudioStorage(root=tmp_path / "audio"), speech=speech
    )

    assert saved == 0
    assert db_session.scalars(select(Transcript)).all() == []
