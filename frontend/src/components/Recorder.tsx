import { useCallback, useEffect, useRef, useState } from 'react'

import { errorMessage, uploadRecording } from '../api'
import { messages } from '../i18n/messages'

const text = messages.recorder

type Status = 'idle' | 'starting' | 'recording' | 'paused' | 'stopped'
type ErrorKind =
  | 'unsupported'
  | 'permissionDenied'
  | 'unavailable'
  | 'deviceMissing'
type Upload = 'idle' | 'uploading' | 'uploaded' | 'failed'

const statusText: Record<Status, string> = {
  idle: text.statusIdle,
  starting: text.statusStarting,
  recording: text.statusRecording,
  paused: text.statusPaused,
  stopped: text.statusStopped,
}

const errorText: Record<ErrorKind, { message: string; guidance: string }> = {
  unsupported: {
    message: text.errorUnsupported,
    guidance: text.errorUnsupportedGuidance,
  },
  permissionDenied: {
    message: text.errorPermissionDenied,
    guidance: text.errorPermissionDeniedGuidance,
  },
  unavailable: {
    message: text.errorUnavailable,
    guidance: text.errorUnavailableGuidance,
  },
  deviceMissing: {
    message: text.errorDeviceMissing,
    guidance: text.errorDeviceMissingGuidance,
  },
}

function formatElapsed(totalSeconds: number): string {
  const pad = (value: number) => String(value).padStart(2, '0')
  const hours = Math.floor(totalSeconds / 3600)
  const minutes = Math.floor((totalSeconds % 3600) / 60)
  const seconds = totalSeconds % 60
  return hours > 0
    ? `${hours}:${pad(minutes)}:${pad(seconds)}`
    : `${pad(minutes)}:${pad(seconds)}`
}

function Recorder({
  meetingId,
  onBusy,
}: {
  meetingId: string
  onBusy?: (busy: boolean) => void
}) {
  const [status, setStatus] = useState<Status>('idle')
  const [elapsedSeconds, setElapsedSeconds] = useState(0)
  const [audioUrl, setAudioUrl] = useState<string | null>(null)
  const [errorKind, setErrorKind] = useState<ErrorKind | null>(null)
  const [devices, setDevices] = useState<MediaDeviceInfo[]>([])
  const [deviceId, setDeviceId] = useState('')
  const [upload, setUpload] = useState<Upload>('idle')
  const [uploadError, setUploadError] = useState('')

  const recorderRef = useRef<MediaRecorder | null>(null)
  const streamRef = useRef<MediaStream | null>(null)
  const chunksRef = useRef<Blob[]>([])
  const timerRef = useRef<number | null>(null)
  // Recorded time is the sum of the running segments, so a pause stops the clock
  // instead of counting the silence.
  const recordedMsRef = useRef(0)
  const segmentStartRef = useRef(0)
  const elapsedMsRef = useRef(0)
  const audioUrlRef = useRef<string | null>(null)
  const blobRef = useRef<Blob | null>(null)
  const mountedRef = useRef(false)

  useEffect(() => {
    mountedRef.current = true
    return () => {
      mountedRef.current = false
      if (timerRef.current !== null) window.clearInterval(timerRef.current)
      recorderRef.current?.stop()
      streamRef.current?.getTracks().forEach((track) => track.stop())
      if (audioUrlRef.current !== null) URL.revokeObjectURL(audioUrlRef.current)
    }
  }, [])

  useEffect(() => {
    onBusy?.(status === 'starting' || status === 'recording' || status === 'paused')
  }, [status, onBusy])

  const refreshDevices = useCallback(async () => {
    const media = navigator.mediaDevices
    if (media?.enumerateDevices === undefined) return
    const inputs = (await media.enumerateDevices()).filter(
      (device) => device.kind === 'audioinput',
    )
    if (!mountedRef.current) return
    setDevices(inputs)
    // A chosen microphone can leave while the page is open, so fall back to the
    // system default rather than keeping a device that is no longer there.
    setDeviceId((current) =>
      current !== '' && !inputs.some((device) => device.deviceId === current)
        ? ''
        : current,
    )
  }, [])

  useEffect(() => {
    void refreshDevices()
    const media = navigator.mediaDevices
    if (media?.addEventListener === undefined) return
    const onChange = () => void refreshDevices()
    media.addEventListener('devicechange', onChange)
    return () => media.removeEventListener('devicechange', onChange)
  }, [refreshDevices])

  function stopTimer() {
    if (timerRef.current !== null) {
      window.clearInterval(timerRef.current)
      timerRef.current = null
    }
  }

  const sendRecording = useCallback(
    async (blob: Blob) => {
      setUpload('uploading')
      setUploadError('')
      try {
        const response = await uploadRecording(
          meetingId,
          blob,
          Math.round(elapsedMsRef.current),
        )
        if (!mountedRef.current) return
        if (response.ok) {
          setUpload('uploaded')
          blobRef.current = null
          return
        }
        setUpload('failed')
        setUploadError(await errorMessage(response))
      } catch {
        if (mountedRef.current) setUpload('failed')
      }
    },
    [meetingId],
  )

  async function startRecording() {
    setErrorKind(null)
    setAudioUrl(null)
    setUpload('idle')
    setUploadError('')
    blobRef.current = null
    if (audioUrlRef.current !== null) {
      URL.revokeObjectURL(audioUrlRef.current)
      audioUrlRef.current = null
    }

    if (navigator.mediaDevices?.getUserMedia === undefined) {
      setErrorKind('unsupported')
      return
    }

    setStatus('starting')
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: deviceId === '' ? true : { deviceId: { exact: deviceId } },
      })
      streamRef.current = stream
      void refreshDevices()
      const recorder = new MediaRecorder(stream)

      chunksRef.current = []
      recorder.ondataavailable = (event) => {
        if (event.data.size > 0) chunksRef.current.push(event.data)
      }
      recorder.onstop = () => {
        const blob = new Blob(chunksRef.current, {
          type: recorder.mimeType || 'audio/webm',
        })
        chunksRef.current = []
        stream.getTracks().forEach((track) => track.stop())
        streamRef.current = null
        recorderRef.current = null
        if (!mountedRef.current) return
        const url = URL.createObjectURL(blob)
        audioUrlRef.current = url
        blobRef.current = blob
        setAudioUrl(url)
        setStatus('stopped')
        // Uploaded straight away, and kept in blobRef so a failure can retry
        // without holding the audio in memory twice.
        void sendRecording(blob)
      }

      recorder.start()
      recorderRef.current = recorder
      setStatus('recording')

      recordedMsRef.current = 0
      segmentStartRef.current = Date.now()
      elapsedMsRef.current = 0
      setElapsedSeconds(0)
      timerRef.current = window.setInterval(() => {
        const running = recorderRef.current?.state === 'recording'
        const live = running ? Date.now() - segmentStartRef.current : 0
        elapsedMsRef.current = recordedMsRef.current + live
        setElapsedSeconds(Math.floor(elapsedMsRef.current / 1000))
      }, 500)
    } catch (error) {
      streamRef.current?.getTracks().forEach((track) => track.stop())
      streamRef.current = null
      setStatus('idle')
      const name = error instanceof DOMException ? error.name : ''
      if (name === 'OverconstrainedError') {
        // The exact device is gone; the list has to catch up before a retry works.
        void refreshDevices()
        setErrorKind('deviceMissing')
        return
      }
      setErrorKind(name === 'NotAllowedError' ? 'permissionDenied' : 'unavailable')
    }
  }

  function pauseRecording() {
    const recorder = recorderRef.current
    if (recorder?.state !== 'recording') return
    recordedMsRef.current += Date.now() - segmentStartRef.current
    recorder.pause()
    setStatus('paused')
    elapsedMsRef.current = recordedMsRef.current
    setElapsedSeconds(Math.floor(recordedMsRef.current / 1000))
  }

  function resumeRecording() {
    const recorder = recorderRef.current
    if (recorder?.state !== 'paused') return
    segmentStartRef.current = Date.now()
    recorder.resume()
    setStatus('recording')
  }

  function stopRecording() {
    const recorder = recorderRef.current
    if (recorder === null) return
    elapsedMsRef.current =
      recorder.state === 'recording'
        ? recordedMsRef.current + (Date.now() - segmentStartRef.current)
        : recordedMsRef.current
    if (recorder.state !== 'inactive') recorder.stop()
    stopTimer()
  }

  const canStop = status === 'recording' || status === 'paused'
  const picking = status === 'starting' || status === 'recording' || status === 'paused'

  return (
    <section>
      <h3>{text.heading}</h3>

      <div role="note" aria-label={text.noticeTitle}>
        <p>
          <strong>{text.noticeTitle}</strong>
        </p>
        <p>{text.noticeBody}</p>
      </div>

      <label>
        {text.microphoneLabel}
        <select
          value={deviceId}
          onChange={(event) => setDeviceId(event.target.value)}
          // A stream keeps the microphone it started with, so changing this
          // mid-recording would promise something it cannot do.
          disabled={picking}
        >
          <option value="">{text.microphoneDefault}</option>
          {devices.map((device, index) => (
            <option key={`${index}-${device.deviceId}`} value={device.deviceId}>
              {device.label || `${text.microphoneFallback} ${index + 1}`}
            </option>
          ))}
        </select>
      </label>
      {devices.every((device) => device.label === '') && (
        <p>{text.microphoneHint}</p>
      )}
      <div role="group" aria-label={text.controlsLabel}>
        {(status === 'idle' || status === 'stopped') && (
          <button type="button" onClick={() => void startRecording()}>
            {text.start}
          </button>
        )}
        {status === 'starting' && (
          <button type="button" disabled>
            {text.starting}
          </button>
        )}
        {status === 'recording' && (
          <button type="button" onClick={pauseRecording}>
            {text.pause}
          </button>
        )}
        {status === 'paused' && (
          <button type="button" onClick={resumeRecording}>
            {text.resume}
          </button>
        )}
        {canStop && (
          <button type="button" onClick={stopRecording}>
            {text.stop}
          </button>
        )}
      </div>

      <p aria-live="polite">
        {text.statusLabel}: <strong>{statusText[status]}</strong>
      </p>
      <p>
        {text.elapsedLabel}: <span>{formatElapsed(elapsedSeconds)}</span>
      </p>

      {errorKind !== null && (
        <div role="alert">
          <p>{errorText[errorKind].message}</p>
          <p>{errorText[errorKind].guidance}</p>
        </div>
      )}

      {audioUrl !== null && (
        <div>
          <p>{text.playbackLabel}</p>
          <audio controls src={audioUrl} />
        </div>
      )}

      {(upload === 'uploading' || upload === 'uploaded') && (
        <p aria-live="polite">
          {text.uploadLabel}:{' '}
          <strong>{upload === 'uploading' ? text.uploading : text.uploaded}</strong>
        </p>
      )}

      {upload === 'failed' && (
        <div role="alert">
          <p>{text.uploadFailed}</p>
          <p>{text.uploadFailedGuidance}</p>
          {uploadError !== '' && <p>{uploadError}</p>}
          <button
            type="button"
            onClick={() => {
              if (blobRef.current !== null) void sendRecording(blobRef.current)
            }}
          >
            {text.uploadRetry}
          </button>
        </div>
      )}
    </section>
  )
}

export default Recorder
