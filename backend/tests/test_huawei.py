from huaweicloudsdksis.v1.model import (
    CollectTranscriberJobResponse,
    TranscriberResult,
)
from huaweicloudsdksis.v1.model import Segment as SisSegment

from app.services.speech import (
    HuaweiSisSpeechToText,
    huawei_result,
    obs_uri,
    transcriber_job,
)


def test_obs_uri_drops_leading_slash():
    assert obs_uri("mom-audio", "/rec.wav") == "obs://mom-audio/rec.wav"


def test_mixed_meeting_lets_sis_detect_language():
    body = transcriber_job(
        "obs://b/k.wav", model_property="chinese_16k_conversation", language=None
    )
    assert body.data_url == "obs://b/k.wav"
    assert body.config._property == "chinese_16k_conversation"
    assert body.config.audio_format == "auto"
    assert body.config.auto_language_detect == "yes"


def test_single_language_meeting_disables_detection():
    body = transcriber_job(
        "obs://b/k.wav", model_property="english_16k_common", language="en"
    )
    assert body.config.auto_language_detect == "no"


def test_result_keeps_timestamps_and_skips_empty_segments():
    response = CollectTranscriberJobResponse(
        job_id="job-1",
        status="finished",
        segments=[
            SisSegment(
                start_time=0, end_time=1500, result=TranscriberResult(text=" 你好 ")
            ),
            SisSegment(
                start_time=1500, end_time=1600, result=TranscriberResult(text="   ")
            ),
            SisSegment(
                start_time=1600, end_time=3200, result=TranscriberResult(text=" hello ")
            ),
        ],
    )

    result = huawei_result(response, language=None, provider="huawei-sis")

    assert result.text == "你好 hello"
    assert result.language == "auto"
    assert result.provider == "huawei-sis"
    assert [(s.start_ms, s.end_ms, s.text) for s in result.segments] == [
        (0, 1500, "你好"),
        (1600, 3200, "hello"),
    ]


def test_result_keeps_caller_language_when_known():
    response = CollectTranscriberJobResponse(job_id="job-2", status="finished")

    result = huawei_result(response, language="zh", provider="huawei-sis")

    assert result.language == "zh"
    assert result.segments == []


def test_missing_credentials_fail_before_upload(tmp_path):
    audio = tmp_path / "part.wav"
    audio.write_bytes(b"RIFF")
    service = HuaweiSisSpeechToText(
        region="",
        project_id="",
        access_key="",
        secret_key="",
        bucket="",
        sis_endpoint="https://example.invalid",
        obs_endpoint="https://example.invalid",
    )

    try:
        service.transcribe(audio, None)
    except RuntimeError as error:
        message = str(error)
        assert "HUAWEI_AK" in message
        assert "HUAWEI_OBS_BUCKET" in message
    else:
        raise AssertionError("expected RuntimeError for missing credentials")
