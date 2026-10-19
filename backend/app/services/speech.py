"""Speech to text.

Whisper runs locally and is the default. Huawei Cloud SIS is the alternative, selected
with SPEECH_PROVIDER=huawei; it needs OBS and SIS credentials, which do not exist in the
development environment yet. Both satisfy the same one-method seam, so swapping the
provider touches this file only. See PROGRESS.md.
"""

import logging
import time
import uuid
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import TYPE_CHECKING, Protocol

from app.core.settings import settings

if TYPE_CHECKING:
    from huaweicloudsdksis.v1.model import (
        CollectTranscriberJobResponse,
        PostTranscriberJobs,
    )

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Segment:
    start_ms: int
    end_ms: int
    text: str


@dataclass(frozen=True)
class SpeechResult:
    text: str
    language: str
    provider: str
    segments: list[Segment]


class SpeechToText(Protocol):
    provider: str

    def transcribe(
        self, audio_path: Path, language: str | None
    ) -> SpeechResult: ...


class WhisperSpeechToText:
    provider = "faster-whisper"

    def __init__(self, model_name: str | None = None) -> None:
        self._model_name = model_name or settings.whisper_model
        self._model = None

    def _model_instance(self):
        if self._model is None:
            # Imported lazily so the API starts without loading a model.
            from faster_whisper import WhisperModel

            self._model = WhisperModel(
                self._model_name, device="cpu", compute_type="int8"
            )
        return self._model

    def transcribe(self, audio_path: Path, language: str | None) -> SpeechResult:
        segments, info = self._model_instance().transcribe(
            str(audio_path), language=language, beam_size=1
        )
        items = [
            Segment(
                start_ms=round(segment.start * 1000),
                end_ms=round(segment.end * 1000),
                text=segment.text.strip(),
            )
            for segment in segments
        ]
        return SpeechResult(
            text=" ".join(item.text for item in items).strip(),
            language=info.language,
            provider=self.provider,
            segments=items,
        )


def obs_uri(bucket: str, key: str) -> str:
    return f"obs://{bucket}/{key.lstrip('/')}"


def transcriber_job(
    data_url: str, *, model_property: str, language: str | None
) -> "PostTranscriberJobs":
    """Build the SIS job body.

    Detection is only safe when the meeting has no single declared language; with one
    language the caller already knows better than detection does.
    """
    from huaweicloudsdksis.v1.model import Config, PostTranscriberJobs

    config = Config(
        _property=model_property,
        audio_format="auto",
        add_punc="yes",
        digit_norm="yes",
        auto_language_detect="no" if language else "yes",
    )
    return PostTranscriberJobs(config=config, data_url=data_url)


def huawei_result(
    response: "CollectTranscriberJobResponse",
    *,
    language: str | None,
    provider: str,
) -> SpeechResult:
    items = []
    for segment in response.segments or []:
        text = segment.result.text.strip() if segment.result else ""
        if text:
            items.append(
                Segment(
                    start_ms=segment.start_time,
                    end_ms=segment.end_time,
                    text=text,
                )
            )
    return SpeechResult(
        text=" ".join(item.text for item in items).strip(),
        # SIS reports no language when it detects one, so the caller keeps its own value.
        language=language or "auto",
        provider=provider,
        segments=items,
    )


class HuaweiSisSpeechToText:
    """Huawei Cloud SIS batch recognition.

    SIS reads its input from OBS, so the driver uploads a temporary object and removes it
    afterwards. The service accepts files up to 5 hours and 300 MB.
    """

    provider = "huawei-sis"

    def __init__(
        self,
        *,
        region: str | None = None,
        project_id: str | None = None,
        access_key: str | None = None,
        secret_key: str | None = None,
        bucket: str | None = None,
        model_property: str | None = None,
        sis_endpoint: str | None = None,
        obs_endpoint: str | None = None,
        poll_seconds: float | None = None,
        timeout_seconds: float | None = None,
    ) -> None:
        self._region = region or settings.huawei_region
        self._project_id = project_id or settings.huawei_project_id
        self._access_key = access_key or settings.huawei_ak
        self._secret_key = secret_key or settings.huawei_sk
        self._bucket = bucket or settings.huawei_obs_bucket
        self._model_property = model_property or settings.huawei_sis_property
        self._sis_endpoint = sis_endpoint or settings.huawei_sis_endpoint or (
            f"https://sis.{self._region}.myhuaweicloud.com"
        )
        self._obs_endpoint = obs_endpoint or settings.huawei_obs_endpoint or (
            f"https://obs.{self._region}.myhuaweicloud.com"
        )
        self._poll_seconds = poll_seconds or settings.huawei_sis_poll_seconds
        self._timeout_seconds = (
            timeout_seconds or settings.huawei_sis_timeout_seconds
        )
        self._sis = None
        self._obs = None

    def _require_config(self) -> None:
        missing = [
            name
            for name, value in {
                "HUAWEI_REGION": self._region,
                "HUAWEI_PROJECT_ID": self._project_id,
                "HUAWEI_AK": self._access_key,
                "HUAWEI_SK": self._secret_key,
                "HUAWEI_OBS_BUCKET": self._bucket,
            }.items()
            if not value
        ]
        if missing:
            raise RuntimeError(
                f"speech_provider=huawei but missing: {', '.join(missing)}"
            )

    def _sis_client(self):
        if self._sis is None:
            from huaweicloudsdkcore.auth.credentials import BasicCredentials
            from huaweicloudsdksis.v1 import SisClient

            credentials = BasicCredentials(
                self._access_key, self._secret_key, self._project_id
            )
            self._sis = (
                SisClient.new_builder()
                .with_credentials(credentials)
                .with_endpoint(self._sis_endpoint)
                .build()
            )
        return self._sis

    def _obs_client(self):
        if self._obs is None:
            from huaweicloudsdkobs.v1.obs_client import ObsClient

            self._obs = ObsClient(
                access_key_id=self._access_key,
                secret_access_key=self._secret_key,
                server=self._obs_endpoint,
            )
        return self._obs

    def _submit(self, data_url: str, language: str | None) -> str:
        from huaweicloudsdksis.v1 import PushTranscriberJobsRequest

        body = transcriber_job(
            data_url, model_property=self._model_property, language=language
        )
        response = self._sis_client().push_transcriber_jobs(
            PushTranscriberJobsRequest(body=body)
        )
        return response.job_id

    def _wait(self, job_id: str) -> "CollectTranscriberJobResponse":
        from huaweicloudsdksis.v1 import CollectTranscriberJobRequest

        deadline = time.monotonic() + self._timeout_seconds
        while True:
            response = self._sis_client().collect_transcriber_job(
                CollectTranscriberJobRequest(job_id=job_id)
            )
            if response.status == "finished":
                return response
            if response.status == "failed":
                raise RuntimeError(f"Huawei SIS job {job_id} failed")
            if time.monotonic() >= deadline:
                raise TimeoutError(
                    f"Huawei SIS job {job_id} did not finish within "
                    f"{self._timeout_seconds:.0f} seconds"
                )
            time.sleep(self._poll_seconds)

    def transcribe(self, audio_path: Path, language: str | None) -> SpeechResult:
        self._require_config()
        key = f"mom-agent/tmp/{uuid.uuid4().hex}{audio_path.suffix}"
        obs = self._obs_client()
        obs.putFile(self._bucket, key, str(audio_path))
        try:
            response = self._wait(self._submit(obs_uri(self._bucket, key), language))
        finally:
            try:
                obs.deleteObject(self._bucket, key)
            except Exception:  # noqa: BLE001 - cleanup must not mask the job error
                logger.warning("Could not delete temporary OBS object %s", key)
        return huawei_result(response, language=language, provider=self.provider)


@lru_cache
def get_speech_to_text() -> SpeechToText:
    if settings.speech_provider == "whisper":
        return WhisperSpeechToText()
    if settings.speech_provider == "huawei":
        return HuaweiSisSpeechToText()
    raise ValueError(f"Unknown speech_provider: {settings.speech_provider}")
