import { useState, type FormEvent } from 'react'

import { apiFetch, errorMessage, type Account } from '../api'
import { messages } from '../i18n/messages'

const text = messages.auth

type Props = {
  onSignedIn: (account: Account) => void
}

function Login({ onSignedIn }: Props) {
  const [registering, setRegistering] = useState(false)
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  async function submit(event: FormEvent) {
    event.preventDefault()
    if (email.trim() === '') {
      setError(text.errorEmailRequired)
      return
    }
    if (registering && password.length < 8) {
      setError(text.errorShortPassword)
      return
    }

    setBusy(true)
    setError('')
    try {
      const response = await apiFetch(
        registering ? '/auth/register' : '/auth/login',
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ email: email.trim(), password }),
        },
      )
      if (!response.ok) {
        const detail = await errorMessage(response)
        setError(detail || (registering ? text.errorFailed : text.errorInvalid))
        return
      }
      onSignedIn((await response.json()) as Account)
    } catch {
      setError(text.errorFailed)
    } finally {
      setBusy(false)
    }
  }

  return (
    <main>
      <h1>{messages.appTitle}</h1>
      <h2>{registering ? text.registerHeading : text.heading}</h2>
      <form className="login" onSubmit={submit}>
        <label>
          {text.emailLabel}
          <input
            type="email"
            autoComplete="email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            required
          />
        </label>
        <label>
          {text.passwordLabel}
          <input
            type="password"
            autoComplete={registering ? 'new-password' : 'current-password'}
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            required
          />
        </label>
        {registering && <p className="hint">{text.passwordHint}</p>}
        <button type="submit" disabled={busy}>
          {busy ? text.working : registering ? text.register : text.signIn}
        </button>
        {error !== '' && (
          <p className="error" role="alert">
            {error}
          </p>
        )}
      </form>
      <button
        type="button"
        onClick={() => {
          setRegistering(!registering)
          setError('')
        }}
      >
        {registering ? text.switchToSignIn : text.switchToRegister}
      </button>
    </main>
  )
}

export default Login
