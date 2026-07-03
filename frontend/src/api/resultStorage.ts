import type { RunTestPayload } from '../types'

const STORAGE_KEY = 'ai-testing-platform:last-run'

export function saveLastRunResult(payload: RunTestPayload): void {
  try {
    sessionStorage.setItem(STORAGE_KEY, JSON.stringify(payload))
  } catch {
    /* ignore quota or privacy errors */
  }
}

export function loadLastRunResult(): RunTestPayload | null {
  try {
    const raw = sessionStorage.getItem(STORAGE_KEY)
    return raw ? (JSON.parse(raw) as RunTestPayload) : null
  } catch {
    return null
  }
}
