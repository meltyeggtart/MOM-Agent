import { useState, type FormEvent } from 'react'

import { apiFetch } from '../api'
import Recorder from '../components/Recorder'
import { messages } from '../i18n/messages'
import type { CreatedMeeting } from './NewMeeting'

const text = messages.meeting

type Props = {
  meeting: CreatedMeeting | null
  onChoose: (meeting: CreatedMeeting | null) => void
}

function Meeting({ meeting, onChoose }: Props) {
  const [reference, setReference] = useState('')
  const [checking, setChecking] = useState(false)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  async function chooseMeeting(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const id = reference.trim()
    if (id === '') return
    setChecking(true)
    setError('')
    try {
      const response = await apiFetch(`/meetings/${id}`)
      if (!response.ok) {
        setError(text.notFound)
        return
      }
      const found = (await response.json()) as { id: string; title: string }
      onChoose({ id: found.id, title: found.title })
    } catch {
      setError(text.notFound)
    } finally {
      setChecking(false)
    }
  }

  return (
    <main>
      <h1>{messages.appTitle}</h1>
      <h2>{text.heading}</h2>

      {meeting === null ? (
        <form onSubmit={(event) => void chooseMeeting(event)}>
          <label>
            {text.referenceLabel}
            <input
              value={reference}
              onChange={(event) => setReference(event.target.value)}
              placeholder={text.referenceHint}
            />
          </label>
          <button type="submit" disabled={checking}>
            {checking ? text.using : text.use}
          </button>
          {error !== '' && <p role="alert">{error}</p>}
        </form>
      ) : (
        <>
          <p>
            {text.recordingFor} <strong>{meeting.title}</strong>{' '}
            {/* Leaving mid-take would discard it, so the way out closes while
                the recorder is busy. */}
            <button
              type="button"
              disabled={busy}
              onClick={() => onChoose(null)}
            >
              {text.change}
            </button>
          </p>
          <Recorder meetingId={meeting.id} onBusy={setBusy} />
        </>
      )}
    </main>
  )
}

export default Meeting
