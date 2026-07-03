/** API request/response types aligned with backend RunTestResponse schema. */

export interface AssertionResult {
  type: string
  expected: string
  actual: string
  passed: boolean
  reason?: string | null
  duration_ms?: number
}

export interface PlanStep {
  action: string
  target?: string | null
  selector?: string | null
  label?: string | null
  text?: string | null
  value?: string | null
  ms?: number | null
  href?: string | null
  selector_strategy?: string | null
  selector_confidence?: number | null
  selector_type?: string | null
  context_url?: string | null
  context_refresh?: boolean | null
  selector_alternatives?: string[] | null
}

export interface ExecutionStep {
  id: string
  step: string
  status: string
  duration_ms: number
  assertions?: AssertionResult[]
}

export interface ExecutionFailure {
  type: string
  message: string
  severity: string
  expected_element?: string | null
  selector?: string | null
  available_context?: Record<string, unknown> | null
  step_id?: string | null
  action?: string | null
  target?: string | null
  expected?: string | null
  actual?: string | null
  exception_type?: string | null
  current_url?: string | null
  page_title?: string | null
  planner_source?: string | null
  screenshot_path?: string | null
  assertion_results?: AssertionResult[]
  website_context_summary?: Record<string, unknown> | null
  timestamp?: string | null
  category?: string | null
  user_message?: string | null
}

export interface ConfidenceSignal {
  signal: string
  contribution?: number
  evidence?: string
}

export interface ConfidenceBreakdown {
  total_confidence?: number
  signals?: ConfidenceSignal[]
}

export interface CoverageArea {
  area: string
  status: string
  reason?: string
}

export interface CoverageReport {
  areas?: CoverageArea[]
  estimated_coverage_percent?: number
}

export interface PlannerMetadata {
  planner_source?: string
  planner_version?: string
  context_version?: string
  generated_at?: string
  validation_score?: number
  planning_time_ms?: number
  provider?: string | null
  context_refreshes?: number
  pages_visited?: string[]
  cache_hits?: number
  cache_misses?: number
  planner_confidence?: number | null
  planner_confidence_label?: string | null
  detected_website_type?: string | null
  detected_intent?: string | null
  primary_navigation?: string[]
  planner_strategy?: string | null
  generated_journey?: string[]
  website_type?: string | null
  business_domain?: string | null
  primary_goal?: string | null
  target_audience?: string | null
  recommended_test_flow?: string[]
  high_risk_areas?: string[]
  testing_priority?: string[]
  analysis_confidence?: number | null
  analysis_reasoning?: string | null
  testing_strategy?: string | null
  confidence_breakdown?: ConfidenceBreakdown | null
  coverage_report?: CoverageReport | null
  execution_priority?: string[]
  strategy_reasoning?: string | null
  estimated_coverage_percent?: number | null
  viewport?: string | null
  browser?: string | null
}

export interface ExecutionSummary {
  total_steps: number
  passed_steps: number
  failed_steps: number
  health: string
}

export interface ReplanningDetail {
  step?: string
  decision?: string
  original?: string
  replacement?: string
  reason?: string
  confidence?: number
}

export interface ReplanningSummary {
  replans_made?: number
  details?: ReplanningDetail[]
}

export interface ExecutionIntelligence {
  adaptive_decisions_made?: number
  steps_skipped?: number
  steps_retried?: number
  modals_dismissed?: number
  steps_replanned?: number
  skip_details?: Array<{ step: string; reason: string; confidence: number }>
  retry_details?: Array<{ step: string; attempts: number; outcome: string }>
  modal_details?: Array<{ step: string; dismissed: boolean }>
  replanning_summary?: ReplanningSummary | null
  version?: string | null
}

export interface WebsiteContextSummary {
  navigation_links?: number
  buttons?: number
  forms?: number
  sections?: number
  detected_components?: number
  hero_sections?: number
  pages_crawled?: number
  context_version?: string
  context_extracted?: boolean
  extraction_error?: string
  website_type?: string
  business_domain?: string
  primary_goal?: string
  target_audience?: string
  recommended_test_flow?: string[]
  high_risk_areas?: string[]
  testing_strategy?: string
  analysis_confidence?: number
  analysis_reasoning?: string
  confidence_breakdown?: ConfidenceBreakdown
  coverage_report?: CoverageReport
  strategy_reasoning?: string
  estimated_coverage_percent?: number
}

export interface DiagnosisReport {
  failure_type?: string
  severity?: string
  confidence?: number
  confidence_label?: string
  ownership?: string
  fix_complexity?: string
  estimated_fix_time?: string
  root_cause?: string
  business_impact?: string
  reasoning?: string
  recommendation?: string
  developer_action?: string
  qa_action?: string
  next_steps?: string[]
  supporting_evidence?: Array<{ source: string; description: string }>
  alternative_hypotheses?: string[]
}

export interface EvidenceConsoleLog {
  type: string
  text: string
}

export interface EvidenceNetworkLog {
  event?: string
  status?: number
  url?: string
  method?: string
  failure?: string
}

export interface EvidencePackage {
  screenshot?: string
  console_logs?: EvidenceConsoleLog[]
  network_logs?: EvidenceNetworkLog[]
  assertions?: unknown[]
  coverage_report?: CoverageReport
  explainability_records?: { signals?: unknown[] }
  dom_snapshot?: unknown
  failure_evidence?: unknown[]
}

export interface RunTestResponse {
  id: string
  goal: string
  status: string
  title: string
  url: string
  http_status: number
  duration_ms: number
  screenshot: string
  ai_plan: PlanStep[]
  ai_plan_source: string
  steps: ExecutionStep[]
  failures: ExecutionFailure[]
  summary: ExecutionSummary
  ai_plan_metadata?: PlannerMetadata | null
  website_context_summary?: WebsiteContextSummary | null
  viewport?: string | null
  browser?: string | null
  screenshot_captured_at?: string | null
  evidence_package?: EvidencePackage | null
  diagnosis_report?: DiagnosisReport | null
  execution_intelligence?: ExecutionIntelligence | null
}

export interface RunTestPayload {
  result: RunTestResponse
  url: string
  goal: string
}

export interface FastApiValidationError {
  msg?: string
}

export type FastApiErrorDetail = string | FastApiValidationError[]
