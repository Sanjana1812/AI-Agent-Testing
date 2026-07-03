const STORAGE_KEY = 'ai-testing-platform:last-run'

export function saveLastRunResult(payload) {
  try {
    sessionStorage.setItem(STORAGE_KEY, JSON.stringify(payload))
  } catch {
    /* ignore quota or privacy errors */
  }
}

export function loadLastRunResult() {
  try {
    const raw = sessionStorage.getItem(STORAGE_KEY)
    return raw ? JSON.parse(raw) : null
  } catch {
    return null
  }
}
