import { Link, useLocation } from 'react-router-dom'
import { API_BASE } from '../api/config'

const STEP_LABELS = {
  open_page: 'Open Page',
  wait: 'Wait',
  click: 'Click',
  fill: 'Fill',
  verify_visible: 'Verify Visible',
  verify_text: 'Verify Text',
  capture: 'Capture Screenshot',
}

function formatStepLabel(step) {
  if (STEP_LABELS[step]) return STEP_LABELS[step]
  const [action, detail] = step.split(':')
  const base = STEP_LABELS[action] || action
  return detail ? `${base} (${detail})` : base
}

function formatPlanStep(step, index) {
  const action = STEP_LABELS[step.action] || step.action
  const details = []
  if (step.target) details.push(`target: ${step.target}`)
  if (step.text) details.push(`text: "${step.text}"`)
  if (step.ms) details.push(`${step.ms}ms`)
  return {
    title: `Step ${index + 1}: ${action}`,
    detail: details.length > 0 ? details.join(' · ') : null,
  }
}

const SEVERITY_STYLES = {
  low: 'border-slate-200 bg-slate-50 text-slate-700',
  medium: 'border-amber-200 bg-amber-50 text-amber-800',
  high: 'border-red-200 bg-red-50 text-red-800',
}

function formatDuration(ms) {
  if (ms == null) return '—'
  if (ms < 1000) return `${ms} ms`
  return `${(ms / 1000).toFixed(2)} s`
}

function StepIcon({ status }) {
  if (status === 'passed') {
    return <span className="text-green-600">✓</span>
  }
  if (status === 'failed') {
    return <span className="text-red-600">✗</span>
  }
  return <span className="text-slate-400">–</span>
}

export default function Results() {
  const { state } = useLocation()
  const result = state?.result
  const goal = state?.goal
  const screenshotUrl = result?.screenshot ? `${API_BASE}${result.screenshot}` : null
  const health = result?.summary?.health
  const isPass = health === 'PASS'

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      {result ? (
        <>
          <div className="rounded-xl border border-slate-200 bg-card p-6 shadow-sm">
            <div className="flex flex-wrap items-start justify-between gap-4">
              <div>
                <h3 className="text-lg font-semibold text-heading">Test Summary</h3>
                <p className="mt-2 text-sm text-slate-600">
                  Structured execution intelligence from Playwright.
                </p>
              </div>
              <span
                className={[
                  'inline-flex rounded-lg px-4 py-2 text-sm font-semibold uppercase tracking-wide',
                  isPass
                    ? 'border border-green-200 bg-green-50 text-green-700'
                    : 'border border-red-200 bg-red-50 text-red-700',
                ].join(' ')}
              >
                {health || '—'}
              </span>
            </div>

            <dl className="mt-6 grid gap-4 border-t border-slate-200 pt-6 text-sm sm:grid-cols-2 lg:grid-cols-4">
              <div>
                <dt className="text-slate-500">Total Steps</dt>
                <dd className="mt-1 text-lg font-semibold text-heading">
                  {result.summary?.total_steps ?? '—'}
                </dd>
              </div>
              <div>
                <dt className="text-slate-500">Passed</dt>
                <dd className="mt-1 text-lg font-semibold text-green-700">
                  {result.summary?.passed_steps ?? '—'}
                </dd>
              </div>
              <div>
                <dt className="text-slate-500">Failed</dt>
                <dd className="mt-1 text-lg font-semibold text-red-700">
                  {result.summary?.failed_steps ?? '—'}
                </dd>
              </div>
              <div>
                <dt className="text-slate-500">Duration</dt>
                <dd className="mt-1 text-lg font-semibold text-heading">
                  {formatDuration(result.duration_ms)}
                </dd>
              </div>
            </dl>

            <dl className="mt-6 grid gap-4 border-t border-slate-200 pt-6 text-sm sm:grid-cols-2">
              <div>
                <dt className="text-slate-500">Run ID</dt>
                <dd className="mt-1 font-mono text-heading">{result.id}</dd>
              </div>
              <div>
                <dt className="text-slate-500">Execution Status</dt>
                <dd className="mt-1 capitalize text-heading">{result.status}</dd>
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
              {(result.goal || goal) && (
                <div className="sm:col-span-2">
                  <dt className="text-slate-500">Testing Goal</dt>
                  <dd className="mt-1 text-heading">{result.goal || goal}</dd>
                </div>
              )}
            </dl>
          </div>

          <div className="rounded-xl border border-slate-200 bg-card p-6 shadow-sm">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <h4 className="text-sm font-semibold text-heading">AI Test Plan</h4>
                <p className="mt-1 text-xs text-slate-500">
                  Generated by:{' '}
                  <span className="font-medium text-heading">
                    {result.ai_plan_source === 'ollama' ? 'Ollama' : 'Fallback'}
                  </span>
                </p>
              </div>
              <span
                className={[
                  'rounded-md border px-3 py-1 text-xs font-medium uppercase tracking-wide',
                  result.ai_plan_source === 'ollama'
                    ? 'border-primary/20 bg-primary/10 text-primary'
                    : 'border-amber-200 bg-amber-50 text-amber-800',
                ].join(' ')}
              >
                {result.ai_plan_source === 'ollama' ? 'Ollama' : 'Fallback'}
              </span>
            </div>
            <ol className="mt-4 space-y-3">
              {(result.ai_plan || []).map((step, index) => {
                const formatted = formatPlanStep(step, index)
                return (
                  <li
                    key={`plan-${index}`}
                    className="rounded-lg border border-slate-200 bg-background px-4 py-3 text-sm"
                  >
                    <p className="font-medium text-heading">
                      {index + 1}. {formatted.title.replace(/^Step \d+: /, '')}
                    </p>
                    {formatted.detail && (
                      <p className="mt-1 text-slate-500">{formatted.detail}</p>
                    )}
                  </li>
                )
              })}
            </ol>
          </div>

          <div className="rounded-xl border border-slate-200 bg-card p-6 shadow-sm">
            <h4 className="text-sm font-semibold text-heading">Execution Timeline</h4>
            <ul className="mt-4 space-y-3">
              {(result.steps || []).map((step) => (
                <li
                  key={step.id}
                  className="flex items-center justify-between rounded-lg border border-slate-200 bg-background px-4 py-3 text-sm"
                >
                  <div className="flex items-center gap-3">
                    <StepIcon status={step.status} />
                    <span className="font-medium text-heading">
                      {formatStepLabel(step.step)}
                    </span>
                  </div>
                  <div className="flex items-center gap-4 text-slate-500">
                    <span className="capitalize">{step.status}</span>
                    <span>{formatDuration(step.duration_ms)}</span>
                  </div>
                </li>
              ))}
            </ul>
          </div>

          <div className="rounded-xl border border-slate-200 bg-card p-6 shadow-sm">
            <h4 className="text-sm font-semibold text-heading">Failure Report</h4>
            {result.failures?.length > 0 ? (
              <div className="mt-4 space-y-3">
                {result.failures.map((failure, index) => (
                  <div
                    key={`${failure.type}-${index}`}
                    className={[
                      'rounded-lg border px-4 py-3 text-sm',
                      SEVERITY_STYLES[failure.severity] || SEVERITY_STYLES.low,
                    ].join(' ')}
                  >
                    <dl className="grid gap-2 sm:grid-cols-3">
                      <div>
                        <dt className="text-xs font-semibold uppercase tracking-wide opacity-70">
                          Type
                        </dt>
                        <dd className="mt-1 font-medium">{failure.type}</dd>
                      </div>
                      <div>
                        <dt className="text-xs font-semibold uppercase tracking-wide opacity-70">
                          Severity
                        </dt>
                        <dd className="mt-1 font-medium capitalize">{failure.severity}</dd>
                      </div>
                      <div className="sm:col-span-1">
                        <dt className="text-xs font-semibold uppercase tracking-wide opacity-70">
                          Message
                        </dt>
                        <dd className="mt-1">{failure.message}</dd>
                      </div>
                    </dl>
                  </div>
                ))}
              </div>
            ) : (
              <p className="mt-4 text-sm text-slate-500">No failures detected.</p>
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
        </>
      ) : (
        <div className="rounded-xl border border-slate-200 bg-card p-6 shadow-sm">
          <h3 className="text-lg font-semibold text-heading">Test Results</h3>
          <p className="mt-4 text-sm text-slate-500">
            No run data available. Start a test to view results.
          </p>
        </div>
      )}

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
