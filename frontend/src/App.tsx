import { useState } from 'react'

import { messages } from './i18n/messages'
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

  return (
    <>
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
