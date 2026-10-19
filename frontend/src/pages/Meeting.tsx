import Recorder from '../components/Recorder'
import { messages } from '../i18n/messages'

const text = messages.meeting

function Meeting() {
  return (
    <main>
      <h1>{messages.appTitle}</h1>
      <h2>{text.heading}</h2>
      <Recorder />
    </main>
  )
}

export default Meeting
