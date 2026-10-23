import { useState } from 'react'

import { messages } from '../i18n/messages'

export type MomTopic = { heading: string; discussion: string }

export type MomAction = {
  task: string
  owner: string | null
  deadline: string | null
}

export type MomContent = {
  title: string
  overview: string
  topics: MomTopic[]
  decisions: string[]
  action_items: MomAction[]
  open_questions: string[]
  internal_notes: string[]
}

export type MomLanguageVersion = { language: string; content: MomContent }

export type MomDocument = {
  source_language: string
  audience: string
  visible_languages: string[]
  versions: MomLanguageVersion[]
}

const text = messages.review

function lines(value: string): string[] {
  return value
    .split('\n')
    .map((line) => line.trim())
    .filter((line) => line !== '')
}

function parseTopics(value: string): MomTopic[] {
  return lines(value).map((line) => {
    const [heading, ...rest] = line.split('|')
    return { heading: heading.trim(), discussion: rest.join('|').trim() }
  })
}

function parseActions(value: string): MomAction[] {
  return lines(value).map((line) => {
    const [task, owner, deadline] = line.split('|')
    return {
      task: task.trim(),
      owner: owner?.trim() || null,
      deadline: deadline?.trim() || null,
    }
  })
}

function showActions(actions: MomAction[]): string {
  return actions
    .map((item) => [item.task, item.owner ?? '', item.deadline ?? ''].join(' | '))
    .join('\n')
}

type Props = {
  content: MomContent
  showInternalNotes: boolean
  onChange: (content: MomContent) => void
}

function MomEditor({ content, showInternalNotes, onChange }: Props) {
  const [title, setTitle] = useState(content.title)
  const [overview, setOverview] = useState(content.overview)
  const [topics, setTopics] = useState(
    content.topics.map((item) => `${item.heading} | ${item.discussion}`).join('\n'),
  )
  const [decisions, setDecisions] = useState(content.decisions.join('\n'))
  const [actions, setActions] = useState(showActions(content.action_items))
  const [questions, setQuestions] = useState(content.open_questions.join('\n'))
  const [notes, setNotes] = useState(content.internal_notes.join('\n'))

  const emit = (patch: Partial<MomContent>) => onChange({ ...content, ...patch })

  return (
    <section className="mom-editor" aria-label={text.editorLabel}>
      <label>
        {text.titleLabel}
        <input
          value={title}
          onChange={(event) => {
            setTitle(event.target.value)
            emit({ title: event.target.value })
          }}
        />
      </label>

      <label>
        {text.overviewLabel}
        <textarea
          value={overview}
          onChange={(event) => {
            setOverview(event.target.value)
            emit({ overview: event.target.value })
          }}
        />
      </label>

      <label>
        {text.topicsLabel}
        <textarea
          value={topics}
          placeholder={text.topicsHint}
          onChange={(event) => {
            setTopics(event.target.value)
            emit({ topics: parseTopics(event.target.value) })
          }}
        />
      </label>

      <label>
        {text.decisionsLabel}
        <textarea
          value={decisions}
          onChange={(event) => {
            setDecisions(event.target.value)
            emit({ decisions: lines(event.target.value) })
          }}
        />
      </label>

      <label>
        {text.actionsLabel}
        <textarea
          value={actions}
          placeholder={text.actionsHint}
          onChange={(event) => {
            setActions(event.target.value)
            emit({ action_items: parseActions(event.target.value) })
          }}
        />
      </label>

      <label>
        {text.questionsLabel}
        <textarea
          value={questions}
          onChange={(event) => {
            setQuestions(event.target.value)
            emit({ open_questions: lines(event.target.value) })
          }}
        />
      </label>

      {showInternalNotes && (
        <label>
          {text.notesLabel}
          <textarea
            value={notes}
            onChange={(event) => {
              setNotes(event.target.value)
              emit({ internal_notes: lines(event.target.value) })
            }}
          />
        </label>
      )}
    </section>
  )
}

export default MomEditor
