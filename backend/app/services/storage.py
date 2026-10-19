"""Audio storage.

Development writes to a local directory. Production targets AWS S3, decided
2026-10-19; this module is the seam where that driver is added, which is why callers
never handle a filesystem path of their own.
"""

import uuid
from collections.abc import Iterable
from pathlib import Path

from app.core.settings import settings


class LocalAudioStorage:
    def __init__(self, root: Path | None = None) -> None:
        self._root = root if root is not None else Path(settings.storage_local_path)

    def save(self, chunks: Iterable[bytes], suffix: str) -> tuple[str, int]:
        key = f"{uuid.uuid4().hex}{suffix}"
        path = self._root / key
        path.parent.mkdir(parents=True, exist_ok=True)
        size = 0
        try:
            with path.open("wb") as handle:
                for chunk in chunks:
                    handle.write(chunk)
                    size += len(chunk)
        except Exception:
            path.unlink(missing_ok=True)
            raise
        return key, size

    def path_for(self, key: str) -> Path:
        return self._root / key

    def delete(self, key: str) -> None:
        (self._root / key).unlink(missing_ok=True)


audio_storage = LocalAudioStorage()


def get_audio_storage() -> LocalAudioStorage:
    return audio_storage
