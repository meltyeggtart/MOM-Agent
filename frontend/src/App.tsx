import { useState } from 'react'

import { messages } from './i18n/messages'
import Meeting from './pages/Meeting'
import NewMeeting from './pages/NewMeeting'

const text = messages.navigation

type Screen = 'newMeeting' | 'meeting'

function App() {
  const [screen, setScreen] = useState<Screen>('newMeeting')

  return (
    <>
      <nav aria-label={text.label}>
        <button
          type="button"
          onClick={() => setScreen('newMeeting')}
          aria-current={screen === 'newMeeting' ? 'page' : undefined}
        >
          {text.newMeeting}
        </button>
        <button
          type="button"
          onClick={() => setScreen('meeting')}
          aria-current={screen === 'meeting' ? 'page' : undefined}
        >
          {text.meeting}
        </button>
      </nav>
      {screen === 'newMeeting' ? <NewMeeting /> : <Meeting />}
    </>
  )
}

export default App
