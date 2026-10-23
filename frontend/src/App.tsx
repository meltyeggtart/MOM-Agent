import { useEffect, useState } from 'react'

import { apiFetch, signedInAccount, type Account } from './api'
import { messages } from './i18n/messages'
import Login from './pages/Login'
import Meeting from './pages/Meeting'
import NewMeeting from './pages/NewMeeting'
import Review from './pages/Review'

const text = messages.navigation

type Screen = 'newMeeting' | 'meeting' | 'review'

const screens: { id: Screen; label: string }[] = [
  { id: 'newMeeting', label: text.newMeeting },
  { id: 'meeting', label: text.meeting },
  { id: 'review', label: text.review },
]

function App() {
  const [screen, setScreen] = useState<Screen>('newMeeting')
  const [account, setAccount] = useState<Account | null>(null)
  const [checking, setChecking] = useState(true)

  useEffect(() => {
    signedInAccount()
      .then(setAccount)
      .catch(() => setAccount(null))
      .finally(() => setChecking(false))
  }, [])

  async function signOut() {
    await apiFetch('/auth/logout', { method: 'POST' }).catch(() => null)
    setAccount(null)
    setScreen('newMeeting')
  }

  if (checking) {
    return (
      <main>
        <h1>{messages.appTitle}</h1>
        <p>{messages.auth.checking}</p>
      </main>
    )
  }

  if (!account) {
    return <Login onSignedIn={setAccount} />
  }

  return (
    <>
      <header className="account">
        <span>
          {messages.auth.signedInAs} {account.email}
        </span>
        <button type="button" onClick={signOut}>
          {messages.auth.signOut}
        </button>
      </header>
      <nav aria-label={text.label}>
        {screens.map((item) => (
          <button
            key={item.id}
            type="button"
            onClick={() => setScreen(item.id)}
            aria-current={screen === item.id ? 'page' : undefined}
          >
            {item.label}
          </button>
        ))}
      </nav>
      {screen === 'newMeeting' && <NewMeeting />}
      {screen === 'meeting' && <Meeting />}
      {screen === 'review' && <Review />}
    </>
  )
}

export default App
