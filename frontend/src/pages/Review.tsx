import { useState } from 'react'

import MomEditor, { type MomDocument } from '../components/MomEditor'
import { messages } from '../i18n/messages'

const text = messages.review

const API_BASE_URL: string =
  import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8000'

const LANGUAGES = ['en', 'zh', 'id'] as const

type MomVersionRow = {
  version_number: number
  content: MomDocument
  ai_generated: boolean
  approved_at: string | null
  approved_by: string | null
  created_at: string
}

type MomResponse = {
  audience: string
  status: string
  versions: MomVersionRow[]
}

function Review() {
  const [meetingId, setMeetingId] = useState('')
  const [audience, setAudience] = useState('internal')
  const [mom, setMom] = useState<MomResponse | null>(null)
  const [draft, setDraft] = useState<MomDocument | null>(null)
  const [language, setLanguage] = useState('en')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')

  const base = `${API_BASE_URL}/meetings/${meetingId}/moms/${audience}`
  const locked = mom?.status === 'approved'
  const current = mom?.versions[mom.versions.length - 1]

  function adopt(response: MomResponse) {
    setMom(response)
    const latest = response.versions[response.versions.length - 1]
    setDraft(structuredClone(latest.content))
  }

  async function request(url: string, init?: RequestInit) {
    setBusy(true)
    setError('')
    setNotice('')
    try {
      const response = await fetch(url, init)
      if (!response.ok) {
        const body = (await response.json().catch(() => null)) as {
          detail?: string
        } | null
        setError(body?.detail ?? text.errorFailed)
        return null
      }
      return (await response.json()) as MomResponse
    } catch {
      setError(text.errorFailed)
      return null
    } finally {
      setBusy(false)
    }
  }

  async function load() {
    const response = await request(base)
    if (response) adopt(response)
  }

  async function save() {
    if (!draft) return
    const response = await request(`${base}/draft`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(draft),
    })
    if (response) {
      adopt(response)
      setNotice(text.saved)
    }
  }

  async function approve() {
    if (!draft) return
    const saved = await request(`${base}/draft`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(draft),
    })
    if (!saved) return
    const response = await request(`${base}/approve`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ approved_by: null }),
    })
    if (response) {
      adopt(response)
      setNotice(text.noticeApproved)
    }
  }

  async function reopen() {
    const response = await request(`${base}/reopen`, { method: 'POST' })
    if (response) {
      adopt(response)
      setNotice(text.reopened)
    }
  }

  function toggleLanguage(code: string) {
    if (!draft) return
    const visible = draft.visible_languages
    const next = visible.includes(code)
      ? visible.filter((item) => item !== code)
      : [...visible, code]
    if (next.length === 0) return
    setDraft({ ...draft, visible_languages: next })
    if (!next.includes(language)) setLanguage(next[0])
  }

  function updateContent(versions: MomDocument['versions']) {
    if (!draft) return
    setDraft({ ...draft, versions })
  }

  const active = draft?.versions.find((item) => item.language === language)

  return (
    <main>
      <h1>{messages.appTitle}</h1>
      <h2>{text.heading}</h2>

      <section>
        <label>
          {text.meetingIdLabel}
          <input
            value={meetingId}
            onChange={(event) => setMeetingId(event.target.value.trim())}
            placeholder={text.meetingIdHint}
          />
        </label>
        <label>
          {text.audienceLabel}
          <select
            value={audience}
            onChange={(event) => setAudience(event.target.value)}
          >
            <option value="internal">{text.audienceInternal}</option>
            <option value="external">{text.audienceExternal}</option>
          </select>
        </label>
        <button type="button" onClick={load} disabled={busy || meetingId === ''}>
          {text.load}
        </button>
      </section>

      {error !== '' && <p role="alert">{error}</p>}
      {notice !== '' && <p role="status">{notice}</p>}

      {mom !== null && draft !== null && (
        <>
          <section aria-label={text.statusLabel}>
            <p>
              {text.statusLabel}: <strong>{mom.status}</strong>
            </p>
            <p>
              {text.versionLabel}: {current?.version_number ?? 0}
              {current?.approved_at
                ? ` · ${text.approvedAt} ${current.approved_at}`
                : ''}
            </p>
            <p>{locked ? text.lockedHint : text.draftHint}</p>
          </section>

          <fieldset>
            <legend>{text.languagesLegend}</legend>
            {LANGUAGES.map((code) => (
              <label key={code}>
                <input
                  type="checkbox"
                  checked={draft.visible_languages.includes(code)}
                  disabled={locked}
                  onChange={() => toggleLanguage(code)}
                />
                {text.languageNames[code]}
              </label>
            ))}
            <p>{text.languagesHint}</p>
          </fieldset>

          <div role="tablist" aria-label={text.languageTabsLabel}>
            {draft.versions
              .filter((item) => draft.visible_languages.includes(item.language))
              .map((item) => (
                <button
                  key={item.language}
                  type="button"
                  role="tab"
                  aria-selected={item.language === language}
                  onClick={() => setLanguage(item.language)}
                >
                  {text.languageNames[item.language as 'en' | 'zh' | 'id']}
                </button>
              ))}
          </div>

          {active && (
            <MomEditor
              key={`${active.language}-${current?.version_number}`}
              content={active.content}
              showInternalNotes={audience === 'internal'}
              onChange={(content) =>
                updateContent(
                  draft.versions.map((item) =>
                    item.language === active.language
                      ? { ...item, content }
                      : item,
                  ),
                )
              }
            />
          )}

          <div>
            <button type="button" onClick={save} disabled={busy || locked}>
              {text.save}
            </button>
            <button type="button" onClick={approve} disabled={busy || locked}>
              {text.approve}
            </button>
            <button type="button" onClick={reopen} disabled={busy || !locked}>
              {text.reopen}
            </button>
          </div>

          <section aria-label={text.historyLabel}>
            <h3>{text.historyLabel}</h3>
            <ul>
              {mom.versions.map((row) => (
                <li key={row.version_number}>
                  {text.versionWord} {row.version_number}
                  {' · '}
                  {row.ai_generated ? text.aiDraft : text.edited}
                  {' · '}
                  {row.approved_at ? text.approved : text.draft}
                </li>
              ))}
            </ul>
          </section>
        </>
      )}
    </main>
  )
}

export default Review
