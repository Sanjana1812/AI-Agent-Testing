import { Link, useLocation } from 'react-router-dom'
import { API_BASE } from '../api/config'

function formatDuration(ms) {
  if (ms == null) return '—'
  if (ms < 1000) return `${ms} ms`
  return `${(ms / 1000).toFixed(2)} s`
}

export default function Results() {
  const { state } = useLocation()
  const result = state?.result
  const goal = state?.goal
  const screenshotUrl = result?.screenshot ? `${API_BASE}${result.screenshot}` : null

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <div className="rounded-xl border border-slate-200 bg-card p-6 shadow-sm">
        <h3 className="text-lg font-semibold text-heading">Test Results</h3>
        <p className="mt-2 text-sm text-slate-600">
          Browser execution completed via Playwright.
        </p>

        {result ? (
          <dl className="mt-6 grid gap-4 border-t border-slate-200 pt-6 text-sm sm:grid-cols-2">
            <div>
              <dt className="text-slate-500">Run ID</dt>
              <dd className="mt-1 font-mono text-heading">{result.id}</dd>
            </div>
            <div>
              <dt className="text-slate-500">Execution Status</dt>
              <dd className="mt-1">
                <span className="inline-flex rounded-md border border-slate-200 bg-background px-3 py-1 text-xs font-semibold uppercase tracking-wide text-primary">
                  {result.status}
                </span>
              </dd>
            </div>
            <div>
              <dt className="text-slate-500">Page Title</dt>
              <dd className="mt-1 text-heading">{result.title || '—'}</dd>
            </div>
            <div>
              <dt className="text-slate-500">HTTP Status</dt>
              <dd className="mt-1 text-heading">{result.http_status ?? '—'}</dd>
            </div>
            <div className="sm:col-span-2">
              <dt className="text-slate-500">Final URL</dt>
              <dd className="mt-1 break-all text-heading">{result.url || '—'}</dd>
            </div>
            <div>
              <dt className="text-slate-500">Duration</dt>
              <dd className="mt-1 text-heading">{formatDuration(result.duration_ms)}</dd>
            </div>
            {goal && (
              <div>
                <dt className="text-slate-500">Testing Goal</dt>
                <dd className="mt-1 text-heading">{goal}</dd>
              </div>
            )}
          </dl>
        ) : (
          <p className="mt-6 text-sm text-slate-500">
            No run data available. Start a test to view results.
          </p>
        )}
      </div>

      <div className="rounded-xl border border-slate-200 bg-card p-6 shadow-sm">
        <h4 className="text-sm font-semibold text-heading">Screenshot Preview</h4>
        {screenshotUrl ? (
          <div className="mt-4 overflow-hidden rounded-lg border border-slate-200 bg-background">
            <img
              src={screenshotUrl}
              alt={`Screenshot of ${result.title || 'page'}`}
              className="w-full"
            />
          </div>
        ) : (
          <div className="mt-4 flex h-40 items-center justify-center rounded-lg border border-dashed border-slate-300 bg-background">
            <p className="text-sm text-slate-500">No screenshot available</p>
          </div>
        )}
      </div>

      <div className="flex gap-3">
        <Link
          to="/run-test"
          className="rounded-lg bg-primary px-5 py-2.5 text-sm font-medium text-white transition hover:bg-primary/90"
        >
          Run Another Test
        </Link>
        <Link
          to="/dashboard"
          className="rounded-lg border border-slate-300 bg-card px-5 py-2.5 text-sm font-medium text-heading transition hover:bg-slate-50"
        >
          Back to Dashboard
        </Link>
      </div>
    </div>
  )
}
