import { API_BASE } from './config'

function formatApiError(detail, status) {
  if (typeof detail === 'string' && detail.trim()) return detail
  if (Array.isArray(detail)) {
    const parts = detail
      .map((item) => (typeof item?.msg === 'string' ? item.msg : null))
      .filter(Boolean)
    if (parts.length) return parts.join('; ')
  }
  if (status === 502 || status === 503 || status === 504) {
    return 'Backend is unavailable. Start the API server on port 8001 and try again.'
  }
  if (status === 500) {
    return 'Test execution failed on the server. If the backend was reloading, wait a few seconds and retry.'
  }
  return `Request failed (${status}). Check that the backend is running on port 8001.`
}

export async function runTest(url, goal) {
  let response
  try {
    response = await fetch(`${API_BASE}/run`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url, goal }),
    })
  } catch {
    throw new Error('Cannot reach the API. Start the backend on port 8001 and try again.')
  }

  if (!response.ok) {
    const error = await response.json().catch(() => ({}))
    throw new Error(formatApiError(error.detail, response.status))
  }

  return response.json()
}
