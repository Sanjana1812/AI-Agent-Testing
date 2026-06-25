import { API_BASE } from './config'

export async function runTest(url, goal) {
  const response = await fetch(`${API_BASE}/run`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ url, goal }),
  })

  if (!response.ok) {
    const error = await response.json().catch(() => ({}))
    const detail = error.detail
    const message = Array.isArray(detail)
      ? detail[0]?.msg
      : typeof detail === 'string'
        ? detail
        : 'Failed to start test run'
    throw new Error(message)
  }

  return response.json()
}
