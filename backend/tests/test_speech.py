from datetime import UTC, datetime
from pathlib import Path

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Meeting, Recording, Transcript
from app.services.speech import WhisperSpeechToText
from app.services.storage import LocalAudioStorage
from app.worker import _language_for, transcribe_pending

FIXTURES = Path(__file__).parent / "fixtures"
KICKOFF = FIXTURES / "kickoff.mp3"
MANDARIN = FIXTURES / "mandarin.mp3"
MIXED = FIXTURES / "mixed.wav"


@pytest.fixture(scope="session")
def speech() -> WhisperSpeechToText:
    return WhisperSpeechToText()


@pytest.fixture
def stored_audio(tmp_path: Path) -> LocalAudioStorage:
    root = tmp_path / "audio"
    root.mkdir()
    for sample in (KICKOFF, MANDARIN, MIXED):
        (root / sample.name).write_bytes(sample.read_bytes())
    return LocalAudioStorage(root=root)


def _meeting(session: Session, languages: list[str] | None = None) -> Meeting:
    meeting = Meeting(
        title="Kickoff",
        meeting_at=datetime(2026, 11, 2, 9, 30, tzinfo=UTC),
        languages=languages or ["en"],
    )
    session.add(meeting)
    session.commit()
    return meeting


def _recording(
    session: Session, meeting: Meeting, key: str = KICKOFF.name
) -> Recording:
    fixture = FIXTURES / key
    recording = Recording(
        meeting_id=meeting.id,
        storage_key=key,
        content_type="audio/wav" if key.endswith(".wav") else "audio/mpeg",
        byte_size=fixture.stat().st_size if fixture.exists() else 0,
    )
    session.add(recording)
    session.commit()
    return recording


def test_language_hint_uses_a_single_declared_language() -> None:
    meeting = Meeting(
        title="Rapat",
        meeting_at=datetime(2026, 11, 2, 9, 30, tzinfo=UTC),
        languages=["id"],
    )

    assert _language_for(meeting) == "id"


def test_language_hint_is_dropped_for_a_mixed_meeting() -> None:
    meeting = Meeting(
        title="Rapat",
        meeting_at=datetime(2026, 11, 2, 9, 30, tzinfo=UTC),
        languages=["en", "id"],
    )

    assert _language_for(meeting) is None


def test_whisper_transcribes_english_speech(speech: WhisperSpeechToText) -> None:
    result = speech.transcribe(KICKOFF, "en")

    text = result.text.lower()
    assert "kickoff" in text
    assert "budget" in text
    assert result.language == "en"
    assert result.provider == "faster-whisper"
    assert result.segments
    assert result.segments[0].start_ms == 0
    assert result.segments[-1].end_ms > 0


def test_whisper_transcribes_mandarin_speech(speech: WhisperSpeechToText) -> None:
    result = speech.transcribe(MANDARIN, None)

    assert result.language == "zh"
    assert "今天" in result.text
    assert "预算" in result.text or "預算" in result.text
    assert "下一步" in result.text


def test_whisper_transcribes_mixed_english_and_mandarin(
    speech: WhisperSpeechToText,
) -> None:
    result = speech.transcribe(MIXED, None)

    text = result.text
    assert "kickoff" in text.lower()
    assert "budget" in text.lower()
    assert "今天" in text
    assert "下一步" in text


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


def test_worker_lets_the_audio_decide_the_language(
    db_session: Session, stored_audio: LocalAudioStorage, speech: WhisperSpeechToText
) -> None:
    meeting = _meeting(db_session, languages=["en", "zh"])
    _recording(db_session, meeting, key=MIXED.name)

    saved = transcribe_pending(db_session, storage=stored_audio, speech=speech)

    assert saved == 1
    transcript = db_session.scalars(select(Transcript)).one()
    assert transcript.language == "zh"
    assert "kickoff" in transcript.text.lower()
    assert "下一步" in transcript.text


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
