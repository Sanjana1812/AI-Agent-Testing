import { useState } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { API_BASE } from '../api/config'
import './Results.css'

function formatDuration(ms) {
  if (ms == null) return null
  if (ms < 1000) return `${ms} ms`
  return `${(ms / 1000).toFixed(2)} s`
}

function parseDurationMs(value) {
  if (typeof value === 'number') return value
  if (value == null || value === '' || value === '—') return 0
  const trimmed = String(value).trim()
  if (trimmed.endsWith('ms')) return parseFloat(trimmed) || 0
  if (trimmed.endsWith('s')) return (parseFloat(trimmed) || 0) * 1000
  return 0
}

function MissingValue({ kind = 'detected' }) {
  return (
    <span className="results-field-value results-field-value--missing">
      {kind === 'captured' ? 'Not captured' : 'Not detected'}
    </span>
  )
}

function displayFieldValue(value, kind = 'detected') {
  if (value == null || value === '' || value === '—') {
    return <MissingValue kind={kind} />
  }
  return value
}

function displayMetricValue(value) {
  if (value == null || value === '—') {
    return <span className="results-metric-card__value results-field-value--missing">Not detected</span>
  }
  return value
}

function displayDurationValue(ms) {
  const formatted = formatDuration(ms)
  if (formatted == null) {
    return <span className="results-metric-card__value results-field-value--missing">Not detected</span>
  }
  return formatted
}

function getPlannerSourceLabel(source) {
  if (!source || source === 'fallback') return 'Fallback'
  return 'AI Planner'
}

function isFallbackSource(source) {
  return !source || source === 'fallback'
}

function humanPlanLabel(step) {
  if (step?.label) return step.label
  return step?.action?.replace(/_/g, ' ') || 'Step'
}

function contextPageName(url) {
  if (!url) return null
  try {
    const path = new URL(url).pathname.replace(/\/$/, '') || '/'
    if (path === '/') return 'Homepage'
    const segment = path.split('/').filter(Boolean).pop() || 'Page'
    return segment.replace(/[-_]/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())
  } catch {
    return 'Page'
  }
}

function computeAverageConfidence(plan) {
  const scores = (plan || [])
    .map((step) => step.selector_confidence)
    .filter((value) => typeof value === 'number')
  if (!scores.length) return null
  return Math.round(scores.reduce((sum, value) => sum + value, 0) / scores.length)
}

function getPlannerConfidence(result) {
  const meta = result?.ai_plan_metadata
  if (meta?.planner_confidence != null) {
    return {
      value: Math.round(meta.planner_confidence),
      label: meta.planner_confidence_label || 'Confidence',
    }
  }
  const avg = computeAverageConfidence(result?.ai_plan)
  if (avg != null) {
    return {
      value: avg,
      label: avg >= 90 ? 'High Confidence' : avg >= 75 ? 'Medium Confidence' : 'Low Confidence',
    }
  }
  if (meta?.validation_score != null) {
    const value = Math.round(meta.validation_score)
    return {
      value,
      label: value >= 90 ? 'High Confidence' : value >= 75 ? 'Medium Confidence' : 'Low Confidence',
    }
  }
  return null
}

function getConfidencePresentation(value) {
  if (value >= 80) {
    return { label: 'High confidence', badgeClass: 'results-badge--confidence-high', barColor: '#639922' }
  }
  if (value >= 50) {
    return { label: 'Good confidence', badgeClass: 'results-badge--confidence-good', barColor: '#185FA5' }
  }
  if (value >= 30) {
    return { label: 'Low confidence', badgeClass: 'results-badge--confidence-low', barColor: '#BA7517' }
  }
  return { label: 'Very low confidence', badgeClass: 'results-badge--confidence-very-low', barColor: '#A32D2D' }
}

function buildJourneyFlow(meta, plan) {
  if (meta?.generated_journey?.length) {
    return meta.generated_journey
  }
  const flow = ['Homepage']
  for (const step of plan || []) {
    if (step.action !== 'click') continue
    const match = step.label?.match(/"([^"]+)"/)
    if (match) {
      flow.push(match[1])
    } else if (step.href) {
      flow.push(contextPageName(step.href) || 'Page')
    }
  }
  if ((plan || []).some((step) => step.action === 'capture') && flow[flow.length - 1] !== 'Screenshot') {
    flow.push('Screenshot')
  }
  return flow.length > 1 ? flow : []
}

function buildExecutionStats(result) {
  const plan = result?.ai_plan || []
  const steps = result?.steps || []
  const meta = result?.ai_plan_metadata || {}

  const assertions = steps.reduce((sum, step) => sum + (step.assertions?.length || 0), 0)
  const navigationEvents = plan.filter((step) =>
    ['click', 'open_page'].includes(step.action),
  ).length
  const waitTimeMs = plan
    .filter((step) => step.action === 'wait')
    .reduce((sum, step) => sum + (step.ms || 0), 0)
  const selfHealingCount = plan.filter(
    (step) => (step.selector_alternatives || []).length > 0,
  ).length

  return {
    actionsExecuted: steps.length,
    assertions,
    navigationEvents,
    waitTimeMs,
    retries: 0,
    selfHealingCount,
    contextRefreshes: meta.context_refreshes ?? 0,
    pagesVisited: meta.pages_visited?.length ?? 0,
  }
}

function formatStepLabel(step) {
  if (!step?.step) return 'Step'
  const [action, detail] = step.step.split(':')
  if (detail) return detail
  return action.replace(/_/g, ' ')
}

function truncateRunId(id) {
  if (!id || id.length <= 16) return id
  return `${id.slice(0, 8)}…${id.slice(-6)}`
}

function getHttpStatusDotClass(status) {
  if (status == null || status === '—') return null
  const code = Number(status)
  if (Number.isNaN(code) || code < 100) return null
  if (code >= 200 && code < 300) return 'results-http-dot--ok'
  if (code >= 400 && code < 500) return 'results-http-dot--warn'
  if (code >= 500) return 'results-http-dot--error'
  if (code >= 300 && code < 400) return 'results-http-dot--warn'
  return null
}

function formatHttpStatus(status) {
  const code = Number(status)
  if (status == null || status === 0 || Number.isNaN(code) || code < 100) {
    return (
      <span className="results-field-value results-field-value--missing">
        — (no request made)
      </span>
    )
  }
  const dotClass = getHttpStatusDotClass(status)
  return (
    <span className="results-http-status">
      {dotClass && <span className={`results-http-dot ${dotClass}`} />}
      {status}
    </span>
  )
}

function formatExecutionStatus(status) {
  if (!status) {
    return <MissingValue kind="detected" />
  }
  const lower = String(status).toLowerCase()
  if (lower === 'failed' || lower === 'error') {
    return (
      <span
        style={{
          display: 'inline-flex',
          alignItems: 'center',
          gap: '5px',
          fontSize: '12px',
          fontWeight: 500,
          padding: '3px 10px',
          borderRadius: '6px',
          background: '#FCEBEB',
          color: '#791F1F',
          border: '0.5px solid #F7C1C1',
        }}
      >
        <i className="ti ti-x" style={{ fontSize: '11px' }} aria-hidden="true" />
        Failed
      </span>
    )
  }
  if (lower === 'success' || lower === 'passed') {
    return (
      <span
        style={{
          display: 'inline-flex',
          alignItems: 'center',
          gap: '5px',
          fontSize: '12px',
          fontWeight: 500,
          padding: '3px 10px',
          borderRadius: '6px',
          background: '#EAF3DE',
          color: '#27500A',
          border: '0.5px solid #C0DD97',
        }}
      >
        <i className="ti ti-check" style={{ fontSize: '11px' }} aria-hidden="true" />
        Success
      </span>
    )
  }
  const capitalized = lower.charAt(0).toUpperCase() + lower.slice(1)
  return (
    <span className="results-field-value" style={{ color: 'var(--text-secondary)', fontWeight: 500 }}>
      {capitalized}
    </span>
  )
}

function isFailedLaunch(executionStatus, httpStatus) {
  const lower = String(executionStatus || '').toLowerCase()
  const isFailed = lower === 'failed' || lower === 'error'
  const code = Number(httpStatus)
  const noHttp = httpStatus == null || httpStatus === 0 || Number.isNaN(code) || code < 100
  return isFailed && noHttp
}

function getActionPill(action) {
  if (action === 'open_page') {
    return { label: 'Navigate', className: 'results-action-pill--navigate', icon: 'world' }
  }
  if (['verify_visible', 'verify_text', 'verify_form'].includes(action)) {
    return { label: 'Verify', className: 'results-action-pill--verify', icon: 'eye' }
  }
  if (['click', 'fill'].includes(action)) {
    return { label: 'Interact', className: 'results-action-pill--click', icon: 'cursor' }
  }
  if (action === 'scroll') {
    return { label: 'Scroll', className: 'results-action-pill--scroll', icon: 'arrows-vertical' }
  }
  if (action === 'capture') {
    return { label: 'Capture', className: 'results-action-pill--capture', icon: 'camera' }
  }
  if (action === 'wait') {
    return { label: 'Wait', className: 'results-action-pill--wait', icon: 'clock' }
  }
  return { label: action?.replace(/_/g, ' ') || 'Step', className: 'results-action-pill--wait', icon: 'clock' }
}

function getTimelineSubline(planStep, execStep) {
  const action = planStep?.action || execStep?.step?.split(':')[0] || ''
  const target = planStep?.target
  if (['verify_visible', 'verify_text', 'verify_form'].includes(action)) {
    const kind = action === 'verify_text' ? 'assert text' : 'assert visibility'
    const detail = target || planStep?.text || 'element'
    return `${kind} · ${String(detail).replace(/_/g, ' ')}`
  }
  if (action === 'open_page') return 'navigate · open page'
  if (action === 'click') return 'interact · click'
  if (action === 'scroll') return 'scroll · section'
  if (action === 'capture') return 'capture · screenshot'
  if (action === 'wait') return 'wait · stabilization'
  if (action === 'fill') return 'interact · fill'
  return action.replace(/_/g, ' ')
}

function formatError(raw) {
  if (!raw) return ''
  return String(raw)
    .replace(/[║═╔╗╚╝╠╣╦╩╬│─┌┐└┘├┤┬┴┼\u2500-\u257F\u2550-\u256C]/g, '')
    .replace(/\.\s+/g, '.\n')
    .replace(/:\s{2,}/g, ':\n')
    .trim()
}

function isBrowserCrashError(message) {
  if (!message) return false
  const lower = String(message).toLowerCase()
  return (
    (lower.includes('playwright') &&
      (lower.includes('not found') || lower.includes('executable') || lower.includes('install'))) ||
    lower.includes('browser crashed') ||
    lower.includes('executable doesn\'t exist') ||
    lower.includes('executable does not exist')
  )
}

const BROWSER_CRASH_SUMMARY =
  'Browser crashed during execution — the Playwright executable was not found. Run: npx playwright install'

function getFailureSummary(failure) {
  if (isBrowserCrashError(failure.message) || isBrowserCrashError(failure.user_message)) {
    return BROWSER_CRASH_SUMMARY
  }
  return failure.user_message || failure.message || 'The test encountered an unexpected issue.'
}

function parseMs(str) {
  if (!str) return 0
  if (str.includes(' s')) return parseFloat(str) * 1000
  if (str.includes(' ms')) return parseFloat(str)
  return 0
}

function isWebsiteIntelEmpty(analysis) {
  if (!analysis) return false
  if (analysis.context_extracted === false) return true
  return (
    (analysis.navigation_links || 0) +
      (analysis.buttons || 0) +
      (analysis.forms || 0) +
      (analysis.sections || 0) +
      (analysis.detected_components || 0) +
      (analysis.hero_sections || 0) ===
    0
  )
}

function formatListValue(items) {
  if (!items || !items.length) {
    return <MissingValue kind="detected" />
  }
  return (
    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.375rem' }}>
      {items.map((item) => (
        <span key={item} className="results-flow-chip">
          {item}
        </span>
      ))}
    </div>
  )
}

function formatReasoningValue(value) {
  if (value == null || value === '' || value === '—') {
    return <span className="results-field-value results-field-value--missing">Not detected</span>
  }
  if (Array.isArray(value)) {
    if (!value.length) {
      return <span className="results-field-value results-field-value--missing">Not detected</span>
    }
    return value.join(' · ')
  }
  return value
}

function getSeverityBadgeClass(severity) {
  const normalized = String(severity || 'low').toLowerCase()
  if (normalized === 'high') return 'results-badge--severity-high'
  if (normalized === 'medium') return 'results-badge--severity-medium'
  return 'results-badge--severity-low'
}

function getSeverityLabel(severity) {
  const normalized = String(severity || 'low').toLowerCase()
  if (normalized === 'high') return 'High'
  if (normalized === 'medium') return 'Medium'
  return 'Low'
}

function Icon({ name, size = 16, className = '' }) {
  const props = { width: size, height: size, viewBox: '0 0 24 24', className: `results-icon ${className}` }
  switch (name) {
    case 'copy':
      return (
        <svg {...props}>
          <rect x="9" y="9" width="13" height="13" rx="2" />
          <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
        </svg>
      )
    case 'arrow-right':
      return (
        <svg {...props}>
          <path d="M5 12h14" />
          <path d="m13 18 6-6-6-6" />
        </svg>
      )
    case 'world':
      return (
        <svg {...props}>
          <circle cx="12" cy="12" r="10" />
          <path d="M2 12h20" />
          <path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z" />
        </svg>
      )
    case 'eye':
      return (
        <svg {...props}>
          <path d="M2 12s3-7 10-7 10 7 10 7-3 7-10 7-10-7-10-7z" />
          <circle cx="12" cy="12" r="3" />
        </svg>
      )
    case 'cursor':
      return (
        <svg {...props}>
          <path d="m9 9-6 16 3-7 7-3z" />
          <path d="M15 5l4 4" />
        </svg>
      )
    case 'arrows-vertical':
      return (
        <svg {...props}>
          <path d="M8 7l4-4 4 4" />
          <path d="M12 3v18" />
          <path d="m16 17-4 4-4-4" />
        </svg>
      )
    case 'camera':
      return (
        <svg {...props}>
          <path d="M14.5 4h-5L7 7H4a2 2 0 0 0-2 2v9a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2V9a2 2 0 0 0-2-2h-3l-2.5-3z" />
          <circle cx="12" cy="13" r="3" />
        </svg>
      )
    case 'clock':
      return (
        <svg {...props}>
          <circle cx="12" cy="12" r="10" />
          <path d="M12 6v6l4 2" />
        </svg>
      )
    case 'check':
      return (
        <svg {...props}>
          <path d="M20 6 9 17l-5-5" />
        </svg>
      )
    case 'x':
      return (
        <svg {...props}>
          <path d="M18 6 6 18" />
          <path d="m6 6 12 12" />
        </svg>
      )
    case 'minus':
      return (
        <svg {...props}>
          <path d="M5 12h14" />
        </svg>
      )
    case 'circle-check':
      return (
        <svg {...props} width={32} height={32}>
          <circle cx="12" cy="12" r="10" />
          <path d="m9 12 2 2 4-4" />
        </svg>
      )
    case 'alert-triangle':
      return (
        <svg {...props}>
          <path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3z" />
          <path d="M12 9v4" />
          <path d="M12 17h.01" />
        </svg>
      )
    case 'chevron-down':
      return (
        <svg {...props}>
          <path d="m6 9 6 6 6-6" />
        </svg>
      )
    case 'photo-off':
      return (
        <svg {...props} width={28} height={28} style={{ opacity: 0.5 }}>
          <path d="M3 3l18 18" />
          <path d="M9 9H4a2 2 0 0 0-2 2v9a2 2 0 0 0 2 2h9" />
          <path d="m15 9 6 6" />
          <path d="M9 13l2 2" />
          <path d="M21 15V9a2 2 0 0 0-2-2h-1" />
        </svg>
      )
    default:
      return null
  }
}

function SectionHeader({ title, subtitle, meta }) {
  return (
    <div className="results-section__header">
      <div>
        <h4 className="results-section__title">{title}</h4>
        {subtitle && <p className="results-section__subtitle">{subtitle}</p>}
      </div>
      {meta && <div className="results-section__header-meta">{meta}</div>}
    </div>
  )
}

function FailureCard({ failure, index, totalSteps, stepLabel, stepId }) {
  const [expanded, setExpanded] = useState(false)
  const cleanError = formatError(failure.message)
  const summary = getFailureSummary(failure)
  const hasTechnical = Boolean(failure.selector || (failure.message && failure.user_message))

  return (
    <div className="results-failure-card">
      <div className="results-failure-card__header">
        <div className="results-failure-card__title">
          <Icon name="alert-triangle" size={16} />
          {failure.type?.replace(/_/g, ' ') || 'Failure'}
        </div>
        <span className={`results-badge ${getSeverityBadgeClass(failure.severity)}`}>
          {getSeverityLabel(failure.severity)}
        </span>
      </div>
      <p className="results-failure-card__summary">{summary}</p>
      {cleanError && (
        <pre className="results-failure-card__raw">{cleanError}</pre>
      )}
      <div className="results-failure-card__footer">
        {hasTechnical ? (
          <button
            type="button"
            className="results-failure-toggle"
            onClick={() => setExpanded((value) => !value)}
          >
            <Icon name="chevron-down" size={12} />
            Technical details
          </button>
        ) : (
          <span />
        )}
        <span className="results-failure-meta">
          Step {stepId || index + 1} of {totalSteps}
          {stepLabel ? ` · ${stepLabel}` : ''}
        </span>
      </div>
      {expanded && hasTechnical && (
        <div style={{ marginTop: '0.75rem', fontSize: '12px', color: '#A32D2D' }}>
          {failure.selector && (
            <p>
              <span style={{ fontWeight: 500 }}>Selector:</span>{' '}
              <code style={{ fontFamily: 'var(--font-mono)' }}>{failure.selector}</code>
            </p>
          )}
        </div>
      )}
    </div>
  )
}

export default function Results() {
  const { state } = useLocation()
  const result = state?.result
  const sourceUrl = state?.url
  const goal = state?.goal
  const screenshotUrl = result?.screenshot ? `${API_BASE}${result.screenshot}` : null
  const health = result?.summary?.health
  const isPass = health === 'PASS'
  const meta = result?.ai_plan_metadata
  const confidence = result ? getPlannerConfidence(result) : null
  const executionStats = result ? buildExecutionStats(result) : null
  const websiteAnalysis = result?.website_context_summary
  const plannerLabel = result ? getPlannerSourceLabel(result.ai_plan_source) : null
  const journeyFlow = result ? buildJourneyFlow(meta, result.ai_plan) : []
  const contextVersion = meta?.context_version || websiteAnalysis?.context_version
  const pagesVisited = meta?.pages_visited?.length ?? executionStats?.pagesVisited
  const confidencePresentation = confidence ? getConfidencePresentation(confidence.value) : null
  const timelineSteps = result?.steps || []
  const maxTimelineMs = Math.max(
    ...timelineSteps.map((step) => parseMs(formatDuration(step.duration_ms))),
    1,
  )
  const showFailureSection = !(isPass && (!result?.failures || result.failures.length === 0))
  const passedCount = result?.summary?.passed_steps ?? 0
  const totalSteps = result?.summary?.total_steps ?? result?.steps?.length ?? 0
  const failedSteps = result?.summary?.failed_steps ?? 0
  const screenshotViewport = result?.viewport ?? meta?.viewport
  const screenshotBrowser = result?.browser ?? meta?.browser
  const screenshotCapturedAt = result?.screenshot_captured_at ?? null
  const contextExtracted = websiteAnalysis?.context_extracted !== false
  const aiWebsiteAnalysis =
    meta?.website_type || websiteAnalysis?.website_type || !contextExtracted
      ? {
          websiteType: meta?.website_type ?? websiteAnalysis?.website_type,
          businessDomain: meta?.business_domain ?? websiteAnalysis?.business_domain,
          primaryGoal: meta?.primary_goal ?? websiteAnalysis?.primary_goal,
          targetAudience: meta?.target_audience ?? websiteAnalysis?.target_audience,
          recommendedJourneys:
            meta?.generated_journey?.length > 0
              ? meta.generated_journey.filter((item) => item !== 'Screenshot')
              : meta?.recommended_test_flow?.length > 0
                ? meta.recommended_test_flow
                : websiteAnalysis?.recommended_test_flow,
          highRiskAreas: meta?.high_risk_areas?.length
            ? meta.high_risk_areas
            : websiteAnalysis?.high_risk_areas,
          testingStrategy: meta?.testing_strategy ?? websiteAnalysis?.testing_strategy,
          analysisConfidence: meta?.analysis_confidence ?? websiteAnalysis?.analysis_confidence,
          analysisReasoning: meta?.analysis_reasoning ?? websiteAnalysis?.analysis_reasoning,
          contextExtracted,
        }
      : null
  const showFailedLaunchNotice = isFailedLaunch(result?.status, result?.http_status)

  async function copyRunId() {
    if (!result?.id) return
    try {
      await navigator.clipboard.writeText(result.id)
    } catch {
      /* ignore clipboard errors */
    }
  }

  function statNumberClass(value, highlight = false) {
    if (highlight && Number(value) > 0) return 'results-metric-card__value results-metric-card__value--highlight'
    if (Number(value) === 0) return 'results-metric-card__value results-metric-card__value--muted'
    return 'results-metric-card__value'
  }

  return (
    <div className="results-page">
      {result ? (
        <>
          <section className="results-section">
            <div className="results-section__header">
              <div>
                <h4 className="results-section__title">Executive summary</h4>
                <p className="results-section__subtitle">High-level overview of this test run</p>
              </div>
              <span className={`results-badge ${isPass ? 'results-badge--pass' : 'results-badge--fail'}`}>
                {health || 'Unknown'}
              </span>
            </div>

            <div className="results-stat-grid">
              <div className="results-metric-card">
                <p className="results-metric-card__label">Total steps</p>
                <p className="results-metric-card__value">
                  {displayMetricValue(result.summary?.total_steps)}
                </p>
              </div>
              <div className="results-metric-card">
                <p className="results-metric-card__label">Passed</p>
                <p className="results-metric-card__value results-metric-card__value--passed">
                  {displayMetricValue(result.summary?.passed_steps)}
                </p>
              </div>
              <div className="results-metric-card">
                <p className="results-metric-card__label">Failed</p>
                <p
                  className={
                    failedSteps === 0
                      ? 'results-metric-card__value results-metric-card__value--failed-dim'
                      : 'results-metric-card__value results-metric-card__value--failed'
                  }
                >
                  {failedSteps}
                </p>
              </div>
              <div className="results-metric-card">
                <p className="results-metric-card__label">Duration</p>
                <p className="results-metric-card__value">{displayDurationValue(result.duration_ms)}</p>
              </div>
            </div>

            <hr className="results-divider" />

            <div className="results-fields-grid">
              <div>
                <p className="results-field-label">Website URL</p>
                <p className="results-field-value">{displayFieldValue(sourceUrl)}</p>
              </div>
              <div>
                <p className="results-field-label">Final URL</p>
                <p className="results-field-value">{displayFieldValue(result.url)}</p>
              </div>
              <div>
                <p className="results-field-label">Run ID</p>
                <p className="results-field-value">
                  <span className="results-run-id">
                    {truncateRunId(result.id)}
                    <button
                      type="button"
                      className="results-copy-btn"
                      onClick={copyRunId}
                      aria-label="Copy run ID"
                    >
                      <Icon name="copy" size={14} />
                    </button>
                  </span>
                </p>
              </div>
              <div>
                <p className="results-field-label">Execution status</p>
                {formatExecutionStatus(result.status)}
              </div>
              {showFailedLaunchNotice ? (
                <div className="results-failed-launch-notice">
                  <i className="ti ti-alert-triangle" aria-hidden="true" />
                  <span>
                    The browser failed to launch before any request was made. Page title and HTTP
                    status are unavailable. Fix:{' '}
                    <code>npx playwright install</code>
                  </span>
                </div>
              ) : (
                <>
                  <div>
                    <p className="results-field-label">Page title</p>
                    <p className="results-field-value">{displayFieldValue(result.title)}</p>
                  </div>
                  <div>
                    <p className="results-field-label">HTTP status</p>
                    <p className="results-field-value">{formatHttpStatus(result.http_status)}</p>
                  </div>
                </>
              )}
              <div>
                <p className="results-field-label">Planner type</p>
                <p className="results-field-value">{plannerLabel}</p>
              </div>
              <div>
                <p className="results-field-label">Planner version</p>
                <p className="results-field-value">{displayFieldValue(meta?.planner_version)}</p>
              </div>
              <div>
                <p className="results-field-label">Planner confidence</p>
                <p className="results-field-value">
                  {confidence
                    ? `${confidence.value}% · ${confidencePresentation?.label}`
                    : displayFieldValue(null)}
                </p>
              </div>
              <div>
                <p className="results-field-label">Pages visited</p>
                <p className="results-field-value">
                  {pagesVisited != null ? pagesVisited : displayFieldValue(null)}
                </p>
              </div>
              <div>
                <p className="results-field-label">Context version</p>
                <p className="results-field-value">{displayFieldValue(contextVersion)}</p>
              </div>
              {(result.goal || goal) && (
                <div style={{ gridColumn: '1 / -1' }}>
                  <p className="results-field-label">Testing goal</p>
                  <p className="results-field-value">{result.goal || goal}</p>
                </div>
              )}
            </div>
          </section>

          <div className="results-dual-grid">
            {confidence && (
              <section className="results-section" style={{ marginBottom: 0 }}>
                <SectionHeader
                  title="Planner confidence"
                  subtitle="How reliably the planner mapped actions to the page"
                />
                <div className="results-confidence-row">
                  <span className="results-confidence-value">{confidence.value}%</span>
                  <span className={`results-badge ${confidencePresentation?.badgeClass}`}>
                    {confidencePresentation?.label}
                  </span>
                  <span
                    className={`results-badge ${
                      isFallbackSource(result.ai_plan_source)
                        ? 'results-badge--fallback'
                        : 'results-badge--ai'
                    }`}
                  >
                    {isFallbackSource(result.ai_plan_source) ? 'Fallback' : 'AI'}
                  </span>
                </div>
                <div className="results-progress">
                  <div className="results-progress__track">
                    <div
                      className="results-progress__fill"
                      style={{
                        width: `${Math.min(confidence.value, 100)}%`,
                        background: confidencePresentation?.barColor,
                      }}
                    />
                  </div>
                </div>
                <hr className="results-planner-meta-divider" />
                <div className="results-planner-meta-grid">
                  <div>
                    <p className="results-planner-meta-label">Planner type</p>
                    <span
                      className={`results-badge ${
                        isFallbackSource(result.ai_plan_source)
                          ? 'results-badge--fallback'
                          : 'results-badge--ai'
                      }`}
                    >
                      {plannerLabel}
                    </span>
                  </div>
                  <div>
                    <p className="results-planner-meta-label">Version</p>
                    <p className="results-planner-meta-value results-planner-meta-value--mono">
                      {displayFieldValue(meta?.planner_version)}
                    </p>
                  </div>
                  <div>
                    <p className="results-planner-meta-label">Context version</p>
                    <p className="results-planner-meta-value results-planner-meta-value--mono">
                      {displayFieldValue(contextVersion)}
                    </p>
                  </div>
                  <div>
                    <p className="results-planner-meta-label">Pages visited</p>
                    <p className="results-planner-meta-value">
                      {pagesVisited != null ? pagesVisited : displayFieldValue(null)}
                    </p>
                  </div>
                </div>
              </section>
            )}

            {websiteAnalysis && (
              <section className="results-section" style={{ marginBottom: 0 }}>
                <SectionHeader
                  title="Website intelligence"
                  subtitle="Structure detected before execution"
                />
                {isWebsiteIntelEmpty(websiteAnalysis) ? (
                  <div className="results-intel-empty-notice">
                    <i className="ti ti-alert-triangle" aria-hidden="true" />
                    <span>
                      {websiteAnalysis?.context_extracted === false
                        ? 'Website structure could not be extracted — analysis and planning used fallback mode'
                        : 'No website structure was extracted — the planner used fallback mode'}
                    </span>
                  </div>
                ) : (
                  <div className="results-intel-grid">
                    {[
                      ['Navigation', websiteAnalysis.navigation_links],
                      ['Buttons', websiteAnalysis.buttons],
                      ['Forms', websiteAnalysis.forms],
                      ['Sections', websiteAnalysis.sections],
                      ['Components', websiteAnalysis.detected_components],
                      ['Hero sections', websiteAnalysis.hero_sections],
                      ['Pages crawled', websiteAnalysis.pages_crawled],
                      ['Context version', websiteAnalysis.context_version],
                    ].map(([label, value]) => {
                      const numeric = typeof value === 'number'
                      const isZero = numeric && value === 0
                      const valueClass = numeric
                        ? isZero
                          ? 'results-intel-tile__value--zero'
                          : 'results-intel-tile__value--active'
                        : 'results-intel-tile__value'
                      return (
                        <div key={label} className="results-intel-tile">
                          <p className="results-intel-tile__label">{label}</p>
                          <p className={valueClass}>
                            {value != null ? value : displayFieldValue(null)}
                          </p>
                        </div>
                      )
                    })}
                  </div>
                )}
              </section>
            )}
          </div>

          {aiWebsiteAnalysis && (
            <section className="results-section">
              <SectionHeader
                title="AI website analysis"
                subtitle="Semantic understanding produced before journey planning"
              />
              <div className="results-fields-grid">
                <div>
                  <p className="results-field-label">Website type</p>
                  <p className="results-field-value">{displayFieldValue(aiWebsiteAnalysis.websiteType)}</p>
                </div>
                <div>
                  <p className="results-field-label">Business domain</p>
                  <p className="results-field-value">{displayFieldValue(aiWebsiteAnalysis.businessDomain)}</p>
                </div>
                <div>
                  <p className="results-field-label">Primary goal</p>
                  <p className="results-field-value">{displayFieldValue(aiWebsiteAnalysis.primaryGoal)}</p>
                </div>
                <div>
                  <p className="results-field-label">Target audience</p>
                  <p className="results-field-value">{displayFieldValue(aiWebsiteAnalysis.targetAudience)}</p>
                </div>
                <div style={{ gridColumn: '1 / -1' }}>
                  <p className="results-field-label">Recommended user journeys</p>
                  {formatListValue(
                    Array.isArray(aiWebsiteAnalysis.recommendedJourneys)
                      ? aiWebsiteAnalysis.recommendedJourneys.filter((item) => item !== 'Screenshot')
                      : null,
                  )}
                </div>
                <div style={{ gridColumn: '1 / -1' }}>
                  <p className="results-field-label">High risk areas</p>
                  {formatListValue(aiWebsiteAnalysis.highRiskAreas)}
                </div>
                <div>
                  <p className="results-field-label">Testing strategy</p>
                  <p className="results-field-value">
                    {displayFieldValue(aiWebsiteAnalysis.testingStrategy)}
                  </p>
                </div>
                <div>
                  <p className="results-field-label">Analysis confidence</p>
                  <p className="results-field-value">
                    {aiWebsiteAnalysis.analysisConfidence != null
                      ? `${Math.round(aiWebsiteAnalysis.analysisConfidence * 100)}%`
                      : displayFieldValue(null)}
                  </p>
                </div>
                {aiWebsiteAnalysis.analysisReasoning && (
                  <div style={{ gridColumn: '1 / -1' }}>
                    <p className="results-field-label">Classification reasoning</p>
                    <p className="results-field-value" style={{ lineHeight: 1.5 }}>
                      {aiWebsiteAnalysis.analysisReasoning}
                    </p>
                  </div>
                )}
              </div>
            </section>
          )}

          <section className="results-section results-section--journey">
            <SectionHeader
              title="AI journey"
              subtitle={`Generated by ${plannerLabel}`}
            />
            {journeyFlow.length > 0 && (
              <>
                <p className="results-field-label">User flow</p>
                <div className="results-flow-wrap">
                  <div className="results-flow">
                    {journeyFlow.map((item, index) => (
                      <span key={`${item}-${index}`} style={{ display: 'inline-flex', alignItems: 'center', gap: '0.5rem' }}>
                        <span className="results-flow-chip">{item}</span>
                        {index < journeyFlow.length - 1 && (
                          <span className="results-flow-arrow" aria-hidden="true">
                            <Icon name="arrow-right" size={14} />
                          </span>
                        )}
                      </span>
                    ))}
                  </div>
                </div>
              </>
            )}
            <p className="results-field-label">Planned steps</p>
            <ol style={{ listStyle: 'none', padding: 0, margin: 0 }}>
              {(result.ai_plan || []).map((step, index) => {
                const pill = getActionPill(step.action)
                return (
                  <li key={`plan-${index}`} className="results-plan-step">
                    <div className="results-plan-step__row">
                      <span className="results-step-num">{index + 1}</span>
                      <span className="results-plan-step__title">{humanPlanLabel(step)}</span>
                      <span className={`results-action-pill ${pill.className}`}>
                        <Icon name={pill.icon} size={12} />
                        {pill.label}
                      </span>
                    </div>
                    {(step.selector || step.context_url || step.selector_confidence != null) && (
                      <details className="results-step-details">
                        <summary>Step details</summary>
                        <dl>
                          {step.selector && (
                            <div>
                              <dt className="results-field-label">Selector</dt>
                              <dd style={{ fontFamily: 'var(--font-mono)', fontSize: '12px' }}>{step.selector}</dd>
                            </div>
                          )}
                          {step.selector_type && (
                            <div>
                              <dt className="results-field-label">Selector type</dt>
                              <dd>{step.selector_type}</dd>
                            </div>
                          )}
                          {step.selector_confidence != null && (
                            <div>
                              <dt className="results-field-label">Confidence</dt>
                              <dd>{Math.round(step.selector_confidence)}%</dd>
                            </div>
                          )}
                          {step.context_url && (
                            <div>
                              <dt className="results-field-label">Context</dt>
                              <dd>{contextPageName(step.context_url)}</dd>
                            </div>
                          )}
                        </dl>
                      </details>
                    )}
                  </li>
                )
              })}
            </ol>
          </section>

          <section className="results-section">
            <SectionHeader
              title="Execution timeline"
              subtitle="Step-by-step run progress"
              meta={`${passedCount} / ${totalSteps} passed`}
            />
            <div className="results-timeline-list">
              {timelineSteps.map((step, index) => {
                const planStep = result.ai_plan?.[index]
                const status = step.status || 'skipped'
                const durationStr = formatDuration(step.duration_ms) ?? ''
                let pct = Math.max((parseMs(durationStr) / maxTimelineMs) * 100, 2)
                let barColor = '#639922'
                if (status === 'failed') {
                  barColor = '#E24B4A'
                } else if (status === 'skipped') {
                  barColor = 'var(--border-strong)'
                  pct = 0
                }
                const rowClass =
                  status === 'failed'
                    ? 'results-timeline-row--failed'
                    : status === 'passed'
                      ? 'results-timeline-row--passed'
                      : 'results-timeline-row--skipped'
                const iconClass =
                  status === 'failed'
                    ? 'results-timeline-icon--failed'
                    : status === 'passed'
                      ? 'results-timeline-icon--passed'
                      : 'results-timeline-icon--skipped'
                const iconName =
                  status === 'failed' ? 'x' : status === 'passed' ? 'check' : 'minus'

                return (
                  <div key={step.id} className={`results-timeline-row ${rowClass}`}>
                    <span className={`results-timeline-icon ${iconClass}`}>
                      <Icon name={iconName} size={11} />
                    </span>
                    <div>
                      <p className="results-timeline-name">
                        {planStep?.label || formatStepLabel(step)}
                      </p>
                      <p className="results-timeline-sub">
                        {getTimelineSubline(planStep, step)}
                      </p>
                    </div>
                    <span
                      className={`results-timeline-status${
                        status === 'skipped' ? ' results-timeline-status--skipped' : ''
                      }`}
                    >
                      {status}
                    </span>
                    <span
                      className={`results-timeline-duration${
                        status === 'skipped' ? ' results-timeline-duration--skipped' : ''
                      }`}
                    >
                      {formatDuration(step.duration_ms) ?? displayFieldValue(null, 'captured')}
                    </span>
                    <div
                      style={{
                        gridColumn: '2 / -1',
                        height: '3px',
                        background: 'var(--surface-0)',
                        borderRadius: '2px',
                        border: '0.5px solid var(--border)',
                        marginTop: '4px',
                        overflow: 'hidden',
                      }}
                    >
                      <div
                        style={{
                          height: '100%',
                          borderRadius: '2px',
                          width: `${pct}%`,
                          background: barColor,
                        }}
                      />
                    </div>
                  </div>
                )
              })}
            </div>
          </section>

          {showFailureSection && (
            <section className="results-section">
              <SectionHeader
                title="Failure report"
                subtitle="Readable explanations with technical details"
              />
              {result.failures?.length > 0 ? (
                result.failures.map((failure, index) => {
                  const stepId = failure.step_id
                  const stepIndex = stepId ? Number(stepId) - 1 : index
                  const planStep = result.ai_plan?.[stepIndex]
                  return (
                    <FailureCard
                      key={`${failure.type}-${index}`}
                      failure={failure}
                      index={index}
                      totalSteps={totalSteps}
                      stepLabel={planStep?.label || formatStepLabel(result.steps?.[stepIndex])}
                      stepId={stepId || String(index + 1)}
                    />
                  )
                })
              ) : (
                <div className="results-failure-empty">
                  <Icon name="circle-check" size={32} className="" style={{ color: '#639922' }} />
                  <p className="results-failure-empty__title">All steps passed</p>
                  <p className="results-failure-empty__subtitle">No failures detected in this run</p>
                </div>
              )}
            </section>
          )}

          {executionStats && (
            <section className="results-section">
              <SectionHeader
                title="Execution statistics"
                subtitle="Runtime activity captured during the test"
              />
              <div className="results-stat-grid results-stat-grid--2x4">
                {[
                  ['Actions executed', executionStats.actionsExecuted, true],
                  ['Assertions', executionStats.assertions, true],
                  ['Navigation events', executionStats.navigationEvents, true],
                  ['Wait time', formatDuration(executionStats.waitTimeMs), false],
                  ['Context refreshes', executionStats.contextRefreshes, false],
                  ['Pages visited', executionStats.pagesVisited, true],
                  ['Self-healing count', executionStats.selfHealingCount, false],
                  ['Retries', executionStats.retries, false],
                ].map(([label, value, highlight]) => (
                  <div key={label} className="results-metric-card">
                    <p className="results-metric-card__label">{label}</p>
                    <p className={statNumberClass(value, highlight)}>{value}</p>
                  </div>
                ))}
              </div>
            </section>
          )}

          <section className="results-section">
            <SectionHeader
              title="Final screenshot"
              subtitle="Visual state at the end of the journey"
            />
            <div className="results-screenshot-meta">
              <div>
                <p className="results-field-label">Captured</p>
                <p className="results-field-value">
                  {screenshotCapturedAt
                    ? new Date(screenshotCapturedAt).toLocaleString()
                    : meta?.generated_at
                      ? new Date(meta.generated_at).toLocaleString()
                      : displayFieldValue(null, 'captured')}
                </p>
              </div>
              <div>
                <p className="results-field-label">Viewport</p>
                <p className="results-field-value">
                  {displayFieldValue(screenshotViewport, 'captured')}
                </p>
              </div>
              <div>
                <p className="results-field-label">Browser</p>
                <p className="results-field-value">
                  {displayFieldValue(screenshotBrowser, 'captured')}
                </p>
              </div>
              <div>
                <p className="results-field-label">Page title</p>
                <p className="results-field-value">{displayFieldValue(result.title)}</p>
              </div>
              <div className="results-screenshot-meta__wide">
                <p className="results-field-label">Final URL</p>
                <p className="results-field-value">{displayFieldValue(result.url)}</p>
              </div>
            </div>
            <div className="results-screenshot-frame">
              {screenshotUrl ? (
                <img src={screenshotUrl} alt={`Screenshot of ${result.title || 'page'}`} />
              ) : (
                <div className="results-screenshot-empty">
                  <Icon name="photo-off" />
                  <p className="results-screenshot-empty__title">No screenshot captured</p>
                  <p className="results-screenshot-empty__subtitle">
                    {!isPass
                      ? 'The test failed before reaching the capture step'
                      : result.status === 'skipped'
                        ? 'The capture step was skipped'
                        : 'No screenshot was captured in this run'}
                  </p>
                </div>
              )}
            </div>
          </section>

          {meta && (
            <CollapsibleReasoning meta={meta} />
          )}
        </>
      ) : (
        <section className="results-section">
          <SectionHeader title="Test results" />
          <p className="results-field-value" style={{ color: 'var(--text-muted)' }}>
            No run data available. Start a test to view results.
          </p>
        </section>
      )}

      <div className="results-cta-row">
        <Link to="/run-test" className="results-cta-primary">
          Run another test
        </Link>
        <Link to="/dashboard" className="results-cta-secondary">
          Back to dashboard
        </Link>
      </div>
    </div>
  )
}

function CollapsibleReasoning({ meta }) {
  const [open, setOpen] = useState(false)

  return (
    <div className="results-collapsible">
      <button type="button" className="results-collapsible__toggle" onClick={() => setOpen((v) => !v)}>
        <div>
          <h4 className="results-section__title">Planner reasoning</h4>
          <p className="results-section__subtitle">
            How the planner interpreted the website and built the journey
          </p>
        </div>
        <span className="results-section__header-meta">{open ? 'Hide' : 'Show'}</span>
      </button>
      {open && (
        <div className="results-collapsible__body">
          <div className="results-reasoning-grid">
            <div>
              <p className="results-field-label">Detected website type</p>
              <p className="results-field-value">{formatReasoningValue(meta.detected_website_type)}</p>
            </div>
            <div>
              <p className="results-field-label">Detected intent</p>
              <p className="results-field-value">{formatReasoningValue(meta.detected_intent)}</p>
            </div>
            <div>
              <p className="results-field-label">Planner strategy</p>
              <p className="results-field-value">{formatReasoningValue(meta.planner_strategy)}</p>
            </div>
            <div style={{ gridColumn: '1 / -1' }}>
              <p className="results-field-label">Primary navigation</p>
              <p className="results-field-value">
                {formatReasoningValue(meta.primary_navigation)}
              </p>
            </div>
            {meta.analysis_reasoning && (
              <div style={{ gridColumn: '1 / -1' }}>
                <p className="results-field-label">Website classification reasoning</p>
                <p className="results-field-value" style={{ lineHeight: 1.5 }}>
                  {meta.analysis_reasoning}
                </p>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
