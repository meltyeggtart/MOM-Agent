// Same-origin by default. The Vite dev server proxies /api to the backend, so the
// session cookie is first-party in development, where it works for any hostname.
export const API_BASE_URL: string = import.meta.env.VITE_API_BASE_URL ?? '/api'

export function apiFetch(path: string, init: RequestInit = {}): Promise<Response> {
  return fetch(`${API_BASE_URL}${path}`, {
    // Sends the HTTP-only session cookie. Without it every call returns 401.
    credentials: 'include',
    ...init,
  })
}

export type Account = {
  id: string
  email: string
}

export async function signedInAccount(): Promise<Account | null> {
  const response = await apiFetch('/auth/me')
  return response.ok ? ((await response.json()) as Account) : null
}

export async function errorMessage(response: Response): Promise<string> {
  const body = (await response.json().catch(() => null)) as {
    detail?: unknown
  } | null
  // Validation errors arrive as a list; only a plain text detail is worth showing.
  return typeof body?.detail === 'string' ? body.detail : ''
}

export function uploadRecording(
  meetingId: string,
  audio: Blob,
  durationMs: number,
): Promise<Response> {
  const form = new FormData()
  form.append('file', audio, `recording.${audio.type.includes('ogg') ? 'ogg' : 'webm'}`)
  form.append('duration_ms', String(durationMs))
  // The browser owns the multipart boundary, so this must not set Content-Type.
  return apiFetch(`/meetings/${meetingId}/recordings`, {
    method: 'POST',
    body: form,
  })
}
