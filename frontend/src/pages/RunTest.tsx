import { FormEvent, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { runTest } from '../api/client'
import { saveLastRunResult } from '../api/resultStorage'
import type { RunTestPayload } from '../types'

export default function RunTest() {
  const navigate = useNavigate()
  const [url, setUrl] = useState('')
  const [goal, setGoal] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()

    const trimmedUrl = url.trim()
    const trimmedGoal = goal.trim()

    if (!trimmedUrl || !trimmedGoal) {
      setError('Application URL and Testing Goal are required.')
      return
    }

    setLoading(true)
    setError('')

    try {
      const data = await runTest(trimmedUrl, trimmedGoal)
      const payload: RunTestPayload = { result: data, url: trimmedUrl, goal: trimmedGoal }
      saveLastRunResult(payload)
      navigate('/results', { state: payload })
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Something went wrong'
      setError(message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="mx-auto max-w-2xl">
      <div className="rounded-xl border border-slate-200 bg-card p-6 shadow-sm">
        <h3 className="text-lg font-semibold text-heading">Run Test</h3>
        <p className="mt-2 text-sm text-slate-600">
          Provide the application URL and describe what you want to test.
        </p>

        <form onSubmit={handleSubmit} className="mt-6 space-y-4" noValidate>
          <div>
            <label htmlFor="url" className="mb-2 block text-sm font-medium text-heading">
              Application URL
            </label>
            <input
              id="url"
              type="url"
              required
              value={url}
              onChange={(event) => setUrl(event.target.value)}
              placeholder="https://example.com"
              className="w-full rounded-lg border border-slate-300 px-4 py-2.5 text-sm outline-none transition focus:border-primary focus:ring-2 focus:ring-primary/20"
            />
          </div>

          <div>
            <label htmlFor="goal" className="mb-2 block text-sm font-medium text-heading">
              Testing Goal
            </label>
            <textarea
              id="goal"
              required
              rows={4}
              value={goal}
              onChange={(event) => setGoal(event.target.value)}
              placeholder="Describe what should be tested, e.g. verify login flow works."
              className="w-full resize-none rounded-lg border border-slate-300 px-4 py-2.5 text-sm outline-none transition focus:border-primary focus:ring-2 focus:ring-primary/20"
            />
          </div>

          {error && (
            <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
              {error}
            </div>
          )}

          <button
            type="submit"
            disabled={loading}
            className="rounded-lg bg-primary px-5 py-2.5 text-sm font-medium text-white transition hover:bg-primary/90 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {loading ? 'Running test...' : 'Run Test'}
          </button>
        </form>
      </div>
    </div>
  )
}
