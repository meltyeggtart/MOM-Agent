import { useState, type FormEvent } from 'react'

import { messages } from '../i18n/messages'

const text = messages.newMeeting

const API_BASE_URL: string =
  import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8000'

type CreatedMeeting = {
  id: string
  title: string
}

function localDateTimeValue(date: Date): string {
  const pad = (value: number) => String(value).padStart(2, '0')
  const day = `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`
  const time = `${pad(date.getHours())}:${pad(date.getMinutes())}`
  return `${day}T${time}`
}

function NewMeeting() {
  const [title, setTitle] = useState('')
  const [meetingAt, setMeetingAt] = useState(() =>
    localDateTimeValue(new Date()),
  )
  const [languages, setLanguages] = useState<string[]>(['en'])
  const [clientCompany, setClientCompany] = useState('')
  const [project, setProject] = useState('')
  const [participants, setParticipants] = useState('')
  const [agenda, setAgenda] = useState('')
  const [location, setLocation] = useState('')
  const [meetingType, setMeetingType] = useState('')
  const [inPerson, setInPerson] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [created, setCreated] = useState<CreatedMeeting | null>(null)

  function toggleLanguage(code: string) {
    setLanguages((current) =>
      current.includes(code)
        ? current.filter((item) => item !== code)
        : [...current, code],
    )
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError('')

    if (title.trim() === '') {
      setError(text.errorTitleRequired)
      return
    }
    if (meetingAt === '') {
      setError(text.errorDateRequired)
      return
    }
    if (languages.length === 0) {
      setError(text.errorLanguageRequired)
      return
    }

    setSaving(true)
    try {
      const response = await fetch(`${API_BASE_URL}/meetings`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          title: title.trim(),
          // The DateTime input carries no time zone; the browser knows the local one.
          meeting_at: new Date(meetingAt).toISOString(),
          languages,
          client_company: clientCompany.trim() || null,
          project: project.trim() || null,
          participants: participants.trim() || null,
          agenda: agenda.trim() || null,
          location: location.trim() || null,
          meeting_type: meetingType.trim() || null,
          is_in_person: inPerson,
        }),
      })

      if (!response.ok) {
        setError(text.errorSaveFailed)
        return
      }

      setCreated((await response.json()) as CreatedMeeting)
    } catch {
      setError(text.errorSaveFailed)
    } finally {
      setSaving(false)
    }
  }

  return (
    <main>
      <h1>{messages.appTitle}</h1>
      <h2>{text.heading}</h2>

      <form onSubmit={handleSubmit}>
        <label>
          {text.titleLabel}
          <input
            value={title}
            onChange={(event) => setTitle(event.target.value)}
            required
          />
        </label>

        <label>
          {text.meetingAtLabel}
          <input
            type="datetime-local"
            value={meetingAt}
            onChange={(event) => setMeetingAt(event.target.value)}
            required
          />
        </label>

        <fieldset>
          <legend>{text.languagesLegend}</legend>
          <label>
            <input
              type="checkbox"
              checked={languages.includes('en')}
              onChange={() => toggleLanguage('en')}
            />
            {text.languageEnglish}
          </label>
          <label>
            <input
              type="checkbox"
              checked={languages.includes('zh')}
              onChange={() => toggleLanguage('zh')}
            />
            {text.languageMandarin}
          </label>
        </fieldset>

        <label>
          {text.clientCompanyLabel}
          <input
            value={clientCompany}
            onChange={(event) => setClientCompany(event.target.value)}
          />
        </label>

        <label>
          {text.projectLabel}
          <input
            value={project}
            onChange={(event) => setProject(event.target.value)}
          />
        </label>

        <label>
          {text.participantsLabel}
          <input
            value={participants}
            onChange={(event) => setParticipants(event.target.value)}
          />
        </label>

        <label>
          {text.agendaLabel}
          <textarea
            value={agenda}
            onChange={(event) => setAgenda(event.target.value)}
          />
        </label>

        <label>
          {text.locationLabel}
          <input
            value={location}
            onChange={(event) => setLocation(event.target.value)}
          />
        </label>

        <label>
          {text.meetingTypeLabel}
          <input
            value={meetingType}
            onChange={(event) => setMeetingType(event.target.value)}
          />
        </label>

        <label>
          <input
            type="checkbox"
            checked={inPerson}
            onChange={(event) => setInPerson(event.target.checked)}
          />
          {text.inPersonLabel}
        </label>

        <button type="submit" disabled={saving}>
          {saving ? text.submitting : text.submit}
        </button>
      </form>

      {error !== '' && <p role="alert">{error}</p>}

      {created !== null && (
        <section>
          <h2>{text.createdHeading}</h2>
          <p>{created.title}</p>
          <p>
            {text.referenceLabel}: {created.id}
          </p>
        </section>
      )}
    </main>
  )
}

export default NewMeeting
